#!/usr/bin/env python3
"""类型域 G 级信号扫描器 + 决策预填表生成器.

配套 core/test-type-matrix.md：G 级（greppable）信号由本脚本机械扫描产出；
S 级（semantic）信号（矩阵各轴清单中标〔S〕的项）由 agent 读代码复核，
本脚本不负责。预填仅基于 G 级；exclude 永不预填（防橡皮图章）。

用法：
    python3 scan_signals.py <仓库路径> [--out 输出文件.yml]

产出（stdout 或 --out 落盘，YAML）：
    scan_meta   仓库、扫描规模、矩阵版本、截断标志（truncated）
    g_signals   每轴 G 级命中（文件:行 + 标签 + 摘要，逐轴截断）
    prefill     修订起点（非决策）：有 G 命中 → include 候选；无 G 命中 → 待复核

确定性保证：目录与命中均排序输出，同一仓库重复运行结果一致。
零第三方依赖；跳过依赖/构建产物目录、二进制与超大文件。
"""
import argparse
import os
import re
import stat as stat_mod
import sys
from pathlib import Path

MATRIX_VERSION = "v1"
MAX_FILE_BYTES = 1_000_000
MAX_FILES = 30_000
MAX_HITS_PER_LABEL = 15

SKIP_DIRS = {
    ".git", ".svn", ".hg", ".idea", ".vscode", "__pycache__", "node_modules",
    "dist", "build", "vendor", "target", "coverage", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "obj", "bin", "out",
}
SKIP_FILE_SUFFIXES = (
    ".min.js", ".min.css", ".map", ".lock",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "go.sum", "poetry.lock",
)
TEXT_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".java", ".go",
    ".rs", ".rb", ".php", ".cs", ".kt", ".swift", ".scala", ".dart", ".sql",
    ".sh", ".yaml", ".yml", ".json", ".toml", ".xml", ".html", ".proto",
    ".gradle", ".kts", ".properties", ".cfg", ".ini", ".j2", ".tf", ".wxml",
}
# 无后缀但有固定文件名的配置文本（如 iOS CocoaPods 清单）
TEXT_FILE_NAMES = {"Podfile"}


def _casefold_charclass(word):
    """把小写词展开为逐字符大小写皆可的字符类序列（kafka → [Kk][Aa][Ff][Kk][Aa]）.

    用于 MQ 词表边界放宽：re.I 会污染边界断言中的字符类（[a-z] 在 re.I 下
    连大写也匹配），使「后非小写字母」的 camelCase 判定无法表达；显式 casefold
    展开后可脱离 re.I，保留组合标识符友好的自定义边界（见「消息队列消费与 ack」）。
    """
    return "".join(f"[{c}{c.upper()}]" for c in word)


# MQ 词表 casefold 展开结果（供 AXIS_PATTERNS 内 f-string 引用）
_MQ_TOKENS = "|".join(
    _casefold_charclass(w)
    for w in ("kafka", "rabbitmq", "rocketmq", "amqp", "pulsar", "bullmq")
)

# 每轴 G 级内容信号：(标签, 正则)。正则命中 ≠ 结论成立——预填表仅供 agent 修订。
AXIS_PATTERNS = {
    "performance": [
        ("缓存依赖", re.compile(r"\b(redis|memcach\w*|@(?:Cacheable|CacheEvict|CachePut)|cache\.(?:get|set|del))\b", re.I)),
        ("无分页全量查询", re.compile(r"SELECT\s+\*\s+FROM", re.I)),
        # 「消息队列」已迁 reliability 轴「消息队列消费与 ack」（对齐矩阵轴3口径）；
        # 轴1 剩余的 MQ 关切（积压/消费速率）是 S 级语义项，由 agent 读代码复核承载
    ],
    "security_business": [
        ("鉴权机制存在", re.compile(r"auth(?!or)\w*|jwt|oauth\w*|rbac|@PreAuthorize|hasRole|requireLogin|鉴权|登录校验", re.I)),
        ("PII 字段", re.compile(r"id_?card|idcard|身份证|手机号|\b(phone|mobile|ssn)\b", re.I)),
        ("可枚举资源 ID", re.compile(r"/\{[a-zA-Z_]*[iI]d\}|:id\b|@PathVariable[^\n]*[iI]d")),
        ("疑似 SQL 拼接", re.compile(r"""f["'](SELECT|INSERT|UPDATE|DELETE)|execute\([^)\n]{0,60}(SELECT|INSERT|UPDATE|DELETE)[^)\n]{0,40}(\+|%s)""", re.I)),
    ],
    "reliability": [
        ("重试逻辑", re.compile(r"retry\w*|backoff|max_?retries|重试", re.I)),
        ("超时配置", re.compile(r"\b(timeout|deadline|context\.WithTimeout|TimeSpan\.From)\b", re.I)),
        # 矩阵轴3 口径「消息队列消费与 ack」：broker 存在性 + 显式 ack 语义；
        # celery/sidekiq 由下方「异步任务/调度」覆盖，此处不重复挂载。
        # 词表边界用双 lookaround（前非任意字母 / 后非小写字母）替代 \b：
        # AMQP_URL / rabbitmq_conn / KafkaProducer 等组合标识符可命中，
        # kafkaesque / pykafka 等小写粘连异义词仍排除（\b 对前者天然漏检）。
        # 本标签不用 re.I：词表经 _casefold_charclass 展开自带大小写，
        # 注解名（Java PascalCase 固定形态）与 basic_ack（协议恒小写）本就精确
        ("消息队列消费与 ack", re.compile(
            rf"(?<![A-Za-z])(?:{_MQ_TOKENS})(?![a-z])"
            r"|@(?:KafkaListener|RabbitListener|JmsListener)"
            r"|basic_(?:ack|nack)\b")),
        ("异步任务/调度", re.compile(r"\b(celery|sidekiq|xxl-?job|quartz|cron\w*|scheduler\w*)\b", re.I)),
        ("断路器", re.compile(r"\b(circuit[_\s-]?breaker|hystrix|resilience4j|sentinel)\b", re.I)),
        ("事务/补偿", re.compile(r"\b(@Transactional|begin[_\s]?transaction|rollback|compensat\w*|saga)\b", re.I)),
    ],
    "concurrency": [
        ("锁与同步原语", re.compile(r"\b(sync\.(?:RWMutex|Mutex)|synchronized|ReentrantLock|threading\.Lock|FOR\s+UPDATE|with_for_update)\b", re.I)),
        ("库存/名额/配额", re.compile(r"stock|inventory|库存|扣减|deduct\w*|seckill|秒杀|quota|配额", re.I)),
        ("唯一性约束", re.compile(r"\b(unique[_\s-]?(?:constraint|key|index)|UNIQUE\s+KEY|unique=True)\b", re.I)),
    ],
    "compatibility": [
        ("浏览器特性 API", re.compile(r"\b(IntersectionObserver|ResizeObserver|navigator\.\w+|matchMedia)\b")),
        ("响应式断点", re.compile(r"@media|useBreakpoint|responsive")),
        # 移动端多端信号：RN/Flutter/小程序的平台分支是"同功能跨端行为可能不一致"的 G 级证据
        ("多端平台分支", re.compile(
            r"\b(Platform\.OS\s*[=!<>]=?|kIsWeb|defaultTargetPlatform\b|TargetPlatform\.(?:iOS|android|macOS)"
            r"|wx\.getSystemInfo\w*|my\.getSystemInfo(?:Sync)?|tt\.getSystemInfo\w*"
            r"|process\.env\.TARO_ENV|UNI_PLATFORM|#ifdef\s+(?:APP-PLUS|MP-WEIXIN|MP-ALIPAY|H5))", re.I)),
        ("系统版本门槛", re.compile(
            r"\b(minSdkVersion|targetSdkVersion|compileSdkVersion|platform\s*:\s*(?:ios|osx)"
            r"|IPHONEOS_DEPLOYMENT_TARGET|MinimumOSVersion|deployment_target|minifyEnabled)\b", re.I)),
    ],
    "accessibility": [
        ("无障碍线索", re.compile(r"\b(aria-[\w-]+|role=|tabindex|focus-visible|<img[^>]*alt)\b", re.I)),
    ],
    "visual": [
        ("已有截图测试", re.compile(r"toHaveScreenshot|screenshot\w*|视觉回归|visual[_\s-]?regression", re.I)),
    ],
    "i18n": [
        ("i18n 框架/格式化", re.compile(r"\b(i18next|vue-i18n|react-intl|formatjs|gettext|Intl\.(?:DateTime|Number)Format|dayjs|date-fns|moment)\b", re.I)),
        # 矩阵轴8 口径「时区处理逻辑」：显式时区 token 即 G 级线索（结论仍须 agent 复核）
        ("时区处理", re.compile(
            r"\b(?:UTC|timezone\w*|time[\s_-]?zone\w*|ZoneId|ZonedDateTime|OffsetDateTime"
            r"|pytz|tzdata|dateutil\.tz|utcOffset)\b|时区|\.tz\(", re.I)),
    ],
    "migration": [
        ("DDL/回填", re.compile(r"ALTER\s+TABLE|CREATE\s+(?:UNIQUE\s+)?INDEX|backfill|回填|db[_\s-]?migrat\w*", re.I)),
        ("多版本 API", re.compile(r"/v[2-9](?:/|\b)|api[_\s-]?version", re.I)),
    ],
    "contract_integration": [
        ("疑似外部调用", re.compile(r"\b(requests\.(?:get|post|put|delete)|http\.(?:Get|Post)|axios\.(?:get|post)|RestTemplate|WebClient|grpc\.(?:Dial|NewClient))\b")),
        ("契约定义", re.compile(r"\b(openapi|swagger|graphql)\b", re.I)),
        # 消息契约（矩阵轴 10 G 级信号，此前仅文档声明无实现）：AsyncAPI / Avro(.avsc)
        # / Pact 契约 / Schema Registry 客户端与配置——按文件内容词匹配
        ("消息契约", re.compile(r"\b(asyncapi|avro|avsc|pact\b|schema[_\s-]?registry)\b", re.I)),
        ("Webhook/回调", re.compile(r"webhook|callback[_\s-]?url|回调", re.I)),
    ],
}

# 每轴 G 级路径信号：(标签, 相对路径匹配正则)。
AXIS_PATH_PATTERNS = {
    "compatibility": [
        # 移动端/小程序工程标志：存在即意味着跨 OS 版本与设备形态的兼容面（此前扫描器对
        # RN/Flutter/小程序全盲，移动端项目这三个轴会全部落"无命中"的假阴性）
        ("移动端工程配置", re.compile(
            r"(^|/)(android/app/build\.gradle(?:\.kts)?|ios/Podfile|pubspec\.yaml"
            r"|project\.config\.json|capacitor\.config\.[jt]s|Info\.plist)$", re.I)),
    ],
    "migration": [
        ("migration 目录", re.compile(r"(^|/)(migrations?|alembic|flyway|liquibase|db/migrate)/", re.I)),
        # .sql 不再全局兜底：根目录散落的 init.sql / dump.sql 等无升级语义，
        # 仅当位于迁移目录上下文（含其子层）内才计为独立文件信号——对齐矩阵轴9口径
        ("migration 文件", re.compile(
            r"(^|/)(migrations?|alembic|flyway|liquibase|db/migrate)/(?:.*/)?[^/]*\.sql$", re.I)),
    ],
    "i18n": [
        ("locale 资源目录", re.compile(r"(^|/)(locales?|i18n|lang)/[^/]+\.(?:json|ya?ml|ts|po)$", re.I)),
        ("gettext 资源", re.compile(r"\.po$", re.I)),
    ],
    "contract_integration": [
        ("proto 契约", re.compile(r"\.proto$", re.I)),
        ("消息契约文件", re.compile(r"\.avsc$", re.I)),
    ],
}

# 前端/客户端存在性（轴 5/6/7 的最低信号，标签固定为「有前端」——矩阵文档按此引用）：
# package.json 含 Web 前端或跨端框架依赖 / pubspec.yaml(Flutter/Dart) / 小程序工程配置，
# 或前端源码文件达到阈值。覆盖 Web、React Native、Flutter、Taro/uni-app 与各系小程序。
FE_DEP_RE = re.compile(
    r'"(react|vue|angular|svelte|next|nuxt|vite|webpack|react-native|@tarojs/taro'
    r'|@dcloudio/[a-z-]+|uni-app|mpvue|wepy)"', re.I)
FLUTTER_MARKER_NAME = "pubspec.yaml"     # Flutter/Dart 工程唯一入口文件，出现即视作客户端信号
MINI_PROGRAM_CONFIGS = {"project.config.json"}   # 微信/字节等小程序工程标志配置
# 样式族（css/scss/less）计入前端源码计数：≥3 个样式文件几乎必然是前端工程，
# 且轴5/6/7 的探测依赖「有前端」信号点亮；.min.css 产物已在 SKIP_FILE_SUFFIXES 排除
FE_EXT_RE = re.compile(r"\.(vue|svelte|html|jsx|tsx|dart|wxml|css|scss|less)$", re.I)
FE_FILE_THRESHOLD = 3

AXES = ["performance", "security_business", "reliability", "concurrency",
        "compatibility", "accessibility", "visual", "i18n", "migration",
        "contract_integration"]
AXIS_NAMES = {
    "performance": "性能效率", "security_business": "业务安全",
    "reliability": "可靠性", "concurrency": "并发一致性",
    "compatibility": "兼容性", "accessibility": "无障碍", "visual": "视觉一致性",
    "i18n": "国际化", "migration": "迁移与升级", "contract_integration": "契约与集成",
}


def iter_files(root: Path, state=None):
    """产出 (path, rel)。os.walk topdown 剪枝 SKIP_DIRS；达到 MAX_FILES 截断时置 state['truncated']。"""
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if n >= MAX_FILES:
                if state is not None:
                    state["truncated"] = True
                return
            rel = (Path(dirpath) / name).relative_to(root).as_posix()
            if any(rel.endswith(s) for s in SKIP_FILE_SUFFIXES):
                continue
            n += 1
            yield Path(dirpath) / name, rel


def sanitize(text: str) -> str:
    # 顺序是硬约束：先清洗控制字符、先截断、剥尾部反斜杠，最后才转义——
    # 截断若落在转义对中间会留下奇数个尾部反斜杠，使 YAML 双引号标量解析失败
    # C0（< 空格）、DEL 与 C1（U+007F–U+009F）控制字符全部置换为空格——YAML 双引号标量均不接受
    text = "".join(ch if (ch >= " " and not ("\x7f" <= ch <= "\x9f")) else " " for ch in text.strip())
    return text[:80].rstrip("\\").replace("\\", "\\\\").replace('"', "'")


def yq(s: str) -> str:
    return '"' + sanitize(s) + '"'


def scan(root: Path):
    hits = {axis: [] for axis in AXES}          # (label, file, line, text)
    label_counts = {}                            # (axis,label) -> n
    fe_dep_found = False
    fl_pubspec_found = False
    mp_config_found = False
    fe_ext_count = 0
    files_scanned = 0
    fallback_files = 0     # 非 UTF-8 源文件数（gb18030 回退读取；中文信号可能部分受损，须在 meta 披露）
    state = {"truncated": False}

    for path, rel in iter_files(root, state):
        files_scanned += 1
        # 路径信号（同样受 MAX_HITS_PER_LABEL 上限，与内容信号口径一致）
        for axis, rules in AXIS_PATH_PATTERNS.items():
            for label, rx in rules:
                key = (axis, label)
                if label_counts.get(key, 0) >= MAX_HITS_PER_LABEL:
                    continue
                if rx.search(rel):
                    hits[axis].append((label, rel, 0, "(路径命中)"))
                    label_counts[key] = label_counts.get(key, 0) + 1
        # 前端/客户端存在性（文件名级判据：Flutter / 小程序不依赖内容即可判定）
        if FE_EXT_RE.search(rel):
            fe_ext_count += 1
        if path.name == FLUTTER_MARKER_NAME:
            fl_pubspec_found = True
        if path.name in MINI_PROGRAM_CONFIGS:
            mp_config_found = True
        # 内容信号（扩展名白名单之外，再放行 Podfile 这类无后缀固定名配置）
        if (path.suffix.lower() not in TEXT_EXTS
                and path.name not in TEXT_FILE_NAMES):
            continue
        try:
            st = path.stat()
            if not stat_mod.S_ISREG(st.st_mode):
                continue  # 字符设备/套接字等（如指向 /dev/zero 的符号链接）不可 read_text
            if st.st_size > MAX_FILE_BYTES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # errors="ignore" 会静默丢弃非 UTF-8 字节——GBK/GB18030 老仓库的中文注释信号
                # （PII/库存/秒杀等 CJK 模式）将整轴假阴性，故显式回退而非忽略
                text = path.read_text(encoding="gb18030", errors="replace")
                fallback_files += 1
        except OSError:
            continue
        if path.name == "package.json" and FE_DEP_RE.search(text):
            fe_dep_found = True
        for axis, rules in AXIS_PATTERNS.items():
            for label, rx in rules:
                key = (axis, label)
                if label_counts.get(key, 0) >= MAX_HITS_PER_LABEL:
                    continue
                for no, line in enumerate(text.split("\n"), 1):
                    if label_counts.get(key, 0) >= MAX_HITS_PER_LABEL:
                        break
                    if rx.search(line):
                        hits[axis].append((label, rel, no, line))
                        label_counts[key] = label_counts.get(key, 0) + 1

    if (fe_dep_found or fl_pubspec_found or mp_config_found
            or fe_ext_count >= FE_FILE_THRESHOLD):
        signal = ("前端/客户端存在（NPM 前端/RN/跨端依赖=" + str(fe_dep_found)
                  + ", Flutter(pubspec)=" + str(fl_pubspec_found)
                  + ", 小程序工程配置=" + str(mp_config_found)
                  + ", 前端源码文件≥" + str(FE_FILE_THRESHOLD) + "：" + str(fe_ext_count) + "）")
        for axis in ("compatibility", "accessibility", "visual"):
            hits[axis].append(("有前端", "(repo)", 0, signal))

    # 去重（同轴同标签同文件同行只留一条）并按轴内 (label, file, line) 排序
    for axis in AXES:
        seen, uniq = set(), []
        for h in hits[axis]:
            k = (h[0], h[1], h[2])
            if k not in seen:
                seen.add(k)
                uniq.append(h)
        hits[axis] = sorted(uniq, key=lambda h: (h[0], h[1], h[2]))
    return hits, files_scanned, fallback_files, state["truncated"]


def render_yaml(hits, files_scanned, fallback_files: int, repo: str, truncated: bool) -> str:
    out = []
    out.append("# G 级信号扫描结果 + 决策预填表（修订起点，不是决策）")
    out.append("# 配套 core/test-type-matrix.md；exclude 永不预填，需 agent 完成 S 级复核与需求信号判定")
    out.append("scan_meta:")
    out.append(f"  repo: {yq(repo)}")
    out.append(f"  matrix_version: {yq(MATRIX_VERSION)}")
    out.append(f"  files_considered: {files_scanned}")
    out.append(f"  truncated: {'true' if truncated else 'false'}")
    out.append(f"  decode_fallback_files: {fallback_files}   # 非 UTF-8 以 gb18030 回退读取的文件数（>0 时中文信号可能有损，人工抽查源文件编码）")
    out.append("  notes:")
    out.append("    - 命中是线索不是结论；逐轴按矩阵六字段决策，预填行仅供修订")
    out.append("    - security_business 为硬默认轴（Web/API 一律至少 standard）")
    if truncated:
        out.append(f"    - 文件数超过 {MAX_FILES} 上限已提前截断——未扫描文件不产生信号，"
                   "exclude 决策不可仅凭本清单")
    out.append("")
    out.append("g_signals:")
    for axis in AXES:
        out.append(f"  {axis}:   # {AXIS_NAMES[axis]}")
        if not hits[axis]:
            out.append("    []")
            continue
        for label, rel, no, text in hits[axis]:
            loc = f"{rel}:{no}" if no else rel
            out.append(f"    - {{label: {yq(label)}, loc: {yq(loc)}, text: {yq(text)}}}")
    out.append("")
    out.append("prefill:   # 修订起点：有 G 命中 → include 候选；无 G 命中 → 待复核（非 exclude）")
    for axis in AXES:
        n = len(hits[axis])
        if axis == "security_business":
            suggest = "include候选（硬默认：Web/API 一律至少 standard）"
        elif n:
            suggest = "include候选（核对需求信号与 S 级后定 depth）"
        else:
            suggest = "待复核（需求信号 + S 级复核后才可决策；exclude 需 G+S 双清单）"
        out.append(f"  {axis}: {{g_hits: {n}, suggest: {yq(suggest)}}}")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="类型域 G 级信号扫描")
    ap.add_argument("repo", help="被测仓库路径")
    ap.add_argument("--out", help="结果落盘路径（缺省打印到 stdout）")
    args = ap.parse_args()

    root = Path(args.repo)
    if not root.is_dir():
        print(f"错误: 仓库路径不存在或不是目录 {root}", file=sys.stderr)
        return 1
    hits, files_scanned, fallback_files, truncated = scan(root)
    yaml_text = render_yaml(hits, files_scanned, fallback_files, str(root), truncated)
    if args.out:
        try:
            Path(args.out).write_text(yaml_text, encoding="utf-8")
        except OSError as e:
            print(f"错误: 无法写入 {args.out}: {e}", file=sys.stderr)
            return 1
        print(f"已写入 {args.out}（考虑文件 {files_scanned}）")
    else:
        print(yaml_text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
