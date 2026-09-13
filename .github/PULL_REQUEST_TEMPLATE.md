# Pull Request 模板

感谢你提交 Pull Request！本项目由零基础开发者与 AI 协作构建，第一次贡献也不必紧张，按本模板填写即可。提交前建议先阅读 CONTRIBUTING.md「五、提交 Pull Request / 合并请求」。国内用户也可在 Gitee 提交合并请求：https://gitee.com/chen-bohan3000/ai-gzt

## 变更类型

请在符合的项上打勾（把 [ ] 改为 [x]）：

- [ ] 🐛 Bug 修复
- [ ] ✨ 新功能
- [ ] 📝 文档变更
- [ ] ♻️ 重构 / 性能优化（不改变外部行为）
- [ ] 🔌 新增 / 修改插件
- [ ] 🔧 构建 / 配置 / CI
- [ ] 其他：

## 关联 Issue

如有关联 Issue 请填写，例如：Closes #123（Gitee 可写：解决 #Ixxxx）

## 改了什么

简要说明本 PR 的具体改动，一个 PR 只解决一件事。

## 为什么改

说明背景与动机，解决什么问题；如有关联讨论请贴链接。

## 如何自测

描述验证步骤、测试环境与结果，例如：
1. Windows 11 + Python 3.11，执行 python main.py 启动；
2. 在设置页修改对应配置，确认行为符合预期；
3. 对改动文件执行 python -m py_compile，无报错。

## 提交前自查清单

- [ ] 本 PR 只解决一件事，分支名符合 feat/xxx、fix/xxx、docs/xxx 约定
- [ ] 已对改动的 Python 文件执行 python -m py_compile，无语法错误
- [ ] 涉及前端页面的改动，已在浏览器中实际走完整流程
- [ ] 未提交 config.json、memory_config.json 等含密钥的本地配置；如涉及配置项变更，已同步修改 config.example.json
- [ ] 如新增第三方依赖：已在插件目录补充 requirements.txt，并在 THIRD_PARTY_LICENSES.md 登记组件与许可证，确认与 Apache-2.0 兼容
- [ ] 如为插件变更：基于 plugin_templates/ 规范开发，未硬编码密钥、未绕过系统禁止目录，按钮无图标
- [ ] 如涉及行为变更，已同步更新 README / CONTRIBUTING 等相关文档

## 补充说明（可选）

截图、兼容性说明、需要维护者重点 review 的地方等。