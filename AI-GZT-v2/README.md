# 未命名项目

> 本工程由「低代码前端开发平台」自动生成，导出时间:2026-10-06T15:46:36.906Z
> 共 34 个页面 / 0 个片段组件。

## 一、快速开始

```bash
npm install      # 安装依赖（首次运行前执行一次）
npm run dev      # 启动开发服务器（默认 http://localhost:5173）
npm run build    # 类型检查 + 生产打包（输出 dist/）
npm run preview  # 本地预览打包结果
```

> 启动后默认进入首页 `/page-o0x2f`。

## 二、目录结构

| 路径 | 说明 |
| --- | --- |
| `src/views/` | 页面组件（每页一个 .vue，路由懒加载按需拉取） |
| `src/components/` | 片段组件（可跨页面复用） |
| `src/router/draft.ts` | 路由表（懒加载 + 404 通配兜底已内置） |
| `src/api/draft.ts` | 接口函数桩（待补全真实请求） |
| `public/assets/` | 图片 / 图标等静态资源 |
| `src/App.vue` | 根组件（挂 router-view + 全局盒模型复位） |

## 三、附产物索引

| 文件 | 面向 | 用途 |
| --- | --- | --- |
| `README.md`（本文件） | 人 | 怎么装 / 怎么跑 / 目录约定 / 接 AI 从哪下手 |
| `schema-manifest.json` | AI | 页面与片段的统计清单（数量可交叉校验） |
| `AI_FILL_GUIDE.md` | AI | 待补全项逐条清单（按类型分组） |
| `PROJECT_STRUCTURE.md` | AI | 结构树 / 数据模型 / 接口清单 / 页面跳转图 |

## 四、接 AI 开发

本产物已按「面向 AI」口径生成，可直接交给 AI 补全业务逻辑:

1. 在每个 .vue 文件中检索 `[AI-FILL]` 标记，按标记处 TODO 注释补全；
2. 待补全项总清单见 `AI_FILL_GUIDE.md`（按事件 / 接口 / 字段 / 数据源 / 片段引用分组）；
3. 接口函数桩见 `src/api/draft.ts`，按占位形参补真实请求库；
4. 后端开发可直接读 `PROJECT_STRUCTURE.md`（结构树 / 数据模型 / 接口清单 / 跳转图）；
5. 项目统计可看 `schema-manifest.json`，用于交叉校验是否漏项。

## 五、已知约定

- **路由地址来源**:在编辑器中配置的 `routePath`（如 `/1`），产物路由表逐字保留；
- **页面文件命名**:由编辑器按页面名安全化生成（如 `1.vue` / `1-2.vue`）；
- **资源引用语法**:在模板中用 `asset:<id>` 引用，产物自动替换为 `public/assets/` 下真实路径；
- **盒模型**:全局已复位 `box-sizing: border-box`（与编辑器画布一致）；

## 六、常见问题

| 问题 | 处理方式 |
| --- | --- |
| 改开发端口 | `vite.config.ts` 的 `server.port`（或 `npm run dev -- --port 3000`） |
| 换后端地址 | 在 `src/api/draft.ts` 统一改 `baseURL`（或引入 axios 实例） |
| 加依赖 | `npm install <包名>`，产物 `package.json` 随后可继续用 |
| 页面不加载 | 检查 `src/router/draft.ts` 中 `path` 与 URL 是否完全一致 |

## 七、技术栈

| 层 | 版本 | 说明 |
| --- | --- | --- |
| Vue | ^3.4 | 组合式 API（`<script setup>`） |
| Vue Router | ^4.3 | 路由（懒加载 + 404 通配兜底） |
| Vite | ^5.2 | 构建工具（+ `@vitejs/plugin-vue`） |
| TypeScript | ^5.4 | 类型检查（`vue-tsc --noEmit`） |
