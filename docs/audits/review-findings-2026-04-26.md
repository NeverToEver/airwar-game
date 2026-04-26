# Code Review: Air War Game Full Audit

**Date:** 2026/04/26
**Status:** **部分修复完成** (12/23 issues fixed)

## Summary

- **Files reviewed:** ~149 Python files, 7 Rust files
- **Issues found:** 23 (3 critical, 10 major, 7 minor, 3 nit)
- **Fixed:** 12 issues

---

## 已修复的问题

- [x] **[OBS]** **`core_bindings.py:38-41`** — 添加了 Rust 模块导入失败的日志记录
- [x] **[PERF]** **`explosion_effect.py:18-19`** — 添加了缓存大小限制（`_MAX_CACHE_SIZE = 64`）和 LRU 淘汰机制
- [x] **[PERF]** **`bullet_manager.py:199`** — 将 `pygame` import 移到模块级别
- [x] **[PERF]** **`player.py:197-200`** — 使用原地过滤 `[:]` 替代创建新列表
- [x] **[CORRECT]** **`bullet_manager.py:142-182`** — 删除了错误的 cleanup 代码
- [x] **[PAT]** **`enemy.py:359`** — 删除了未使用的 `agg_tracking_x/y` dead code
- [x] **[PERF]** **`explosion_effect.py:199`** — `pygame` import 已在模块级别
- [x] **[ARCH]** **`game_integrator.py`** — 层违规重构，通过 IGameScene 接口访问 ✅
- [x] **[ARCH]** **`state_machine.py:57-58`** — 移除空 transition() 方法 ✅
- [x] **[PERF]** **`explosion_effect.py:310-329`** — 实现 flash surface 缓存 ✅
- [x] **[CORRECT]** **敌人子弹 cleanup** — 统一清理接口 ✅
- [x] **[PERF]** **PersistentSpatialHash** — 碰撞检测增量更新 ✅

---

## Critical Issues

- [x] **[ARCH]** **`game_integrator.py`** — 层违规 ✅
- [x] **[ARCH]** **`state_machine.py`** — 空 transition() ✅
- [ ] **[BUG]** **`enemy.py:811`** — `BOSS_AIM_BULLET_DAMAGE_BASE` vs `B.BULLET_DAMAGE_BASE` 语义不一致

---

## Major Issues (未修复)

- [ ] **[BUG]** **`enemy.py:369-385`** — aggressive movement 的 `amplitude` 默认值问题
- [ ] **[BUG]** **`collision_controller.py:369-385`** — aggressive movement 问题（代码已变更，需重新确认）
- [ ] **[ARCH]** **`game_integrator.py:500-513`** — 强制状态切换绕过状态机验证
- [ ] **[ARCH]** **`scene_director.py:398-408`** — 访问私有属性 `_mother_ship_integrator`
- [ ] **[SEC]** **`database.py:29-30`** — SHA-256 无 salt 哈希（低风险）

---

## Minor Issues (未修复)

- [ ] **[PERF]** **`explosion_effect.py:231-239`** — sparks/debris 双重迭代（设计如此）
- [ ] **[CORRECT]** **`collision_controller.py:292`** — `break` 位置可优化
- [ ] **[ARCH]** **`mother_ship_state.py:52,82`** — `pygame.time.get_ticks()` 硬编码

---

## Nit (未修复)

- [ ] **[PAT]** **`enemy.py:380-381`** — aggressive 的 ternary 设计如此
- [ ] **[DOC]** **`movement.rs:63-68`** — 保留参数作为未来扩展占位符
- [ ] **[STYLE]** **`mouse_interaction.py:6-159`** — Mixin 可合并

---

## 详细报告

完整审计结果见 `docs/` 目录历史文件。MAINTENANCE_GUIDE.md 包含最新维护状态。
