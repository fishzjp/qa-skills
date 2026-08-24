/**
 * qa-skills 插件（DeepSeek Harness / dsh）。
 *
 * 把本仓库 skills/ 下的 10 个测试技能 + core/ 共享知识库注册为 dsh 运行时技能：
 * 模型经 `skill` 工具按需加载正文，相对路径引用（../core/*.md、references/、scripts/）
 * 经 resourceBase 指向的技能目录解析。仅用 Node 内建模块，无构建步骤、零运行时依赖
 * （dsh 把 @deepseek-ai/* 嵌在自身安装内，插件无法直接 import，全部经注入的 ctx 访问）。
 *
 * 参照模式：obra/superpowers 的 dsh 支持实现（PR #2144）。
 */

import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

/** Cordis 插件名（loader 诊断与补丁层 insert id 使用）。 */
export const name = 'dsh-qa-skills';

/** 依赖的宿主服务：技能注册表就绪后才激活。 */
export const inject = ['skills'];

/** 技能源目录：<包根>/skills。 */
const skillsDir = resolve(dirname(fileURLToPath(import.meta.url)), '../../skills');

/** 共享知识库单元：不面向任务触发（其余 skill 以文件路径引用其内容，不经 skill 工具）。 */
const DEPENDENCY_UNIT = 'core';

/**
 * 拆分 SKILL.md：frontmatter 字段（仅支持单行 key: value）与指令正文。
 * @param {string} raw - SKILL.md 原始内容。
 * @returns {{name?: string, description?: string, whenToUse?: string, body: string}}
 */
const parseSkill = (raw) => {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!match) return { body: raw.trim() };

  const fields = {};
  for (const line of match[1].split(/\r?\n/)) {
    const field = line.match(/^([A-Za-z][\w-]*):\s*(.+)$/);
    if (field) fields[field[1]] = field[2].trim().replace(/^["'](.*)["']$/, '$1');
  }
  return { ...fields, body: match[2].trim() };
};

/**
 * 读取全部技能单元（目录含 SKILL.md 才算），跳过并告警不可读或畸形单元。
 * @param {{warn: (message: string) => void}} logger - 宿主日志器。
 * @returns {Array<{name: string, description: string, whenToUse?: string, content: string, source: string, path: string, invocation?: {modelInvocable: boolean, userInvocable: boolean}, resourceBase: {kind: 'directory', path: string}}>}
 */
const readSkills = (logger) => {
  let entries;
  try {
    entries = readdirSync(skillsDir, { withFileTypes: true });
  } catch (error) {
    logger.warn(`dsh-qa-skills: cannot read ${skillsDir}: ${error.message}`);
    return [];
  }

  const skills = [];
  for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
    if (!entry.isDirectory()) continue;
    const skillDir = join(skillsDir, entry.name);
    const skillPath = join(skillDir, 'SKILL.md');

    let raw;
    try {
      raw = readFileSync(skillPath, 'utf8');
    } catch (error) {
      logger.warn(`dsh-qa-skills: cannot read ${skillPath}: ${error.message}`);
      continue;
    }

    const skill = parseSkill(raw);
    if (!skill.name || !skill.description || !skill.body) {
      logger.warn(`dsh-qa-skills: ${skillPath} needs name and description frontmatter and a body`);
      continue;
    }

    skills.push({
      name: skill.name,
      description: skill.description,
      ...(skill.whenToUse ? { whenToUse: skill.whenToUse } : {}),
      content: skill.body,
      source: 'bundled',
      path: skillPath,
      // core 是共享知识库依赖单元：双不可调用，仅作为相对路径引用的落点存在
      ...(skill.name === DEPENDENCY_UNIT
        ? { invocation: { modelInvocable: false, userInvocable: false } }
        : {}),
      resourceBase: { kind: 'directory', path: skillDir },
    });
  }
  return skills;
};

/**
 * 插件入口：注册全部技能单元。每次注册都是随插件自身 fiber 销毁的 Cordis effect。
 * @param {import('@deepseek-ai/cordis').Context} ctx - 宿主注入的插件上下文。
 */
export function apply(ctx) {
  const skills = readSkills(ctx.logger);
  for (const skill of skills) ctx.skills.register(skill);

  // 安装完整性哨兵：缺 core 意味着引用路径断裂（其余 skill 的 ../core/*.md 会指向不存在目录）
  if (!skills.some((skill) => skill.name === DEPENDENCY_UNIT)) {
    ctx.logger.warn(
      `dsh-qa-skills: dependency unit "core" is missing from ${skillsDir}; relative references from other skills will break`,
    );
  }
  ctx.logger.info(`dsh-qa-skills: registered ${skills.length} skill unit(s) from ${skillsDir}`);
}
