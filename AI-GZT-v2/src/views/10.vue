<!--
  页面《10》　路由:/10（10）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <div class="box-div-2jblc">
    <div class="box-div-hwfxb">
      <div class="box-div-lzyyr">
        <!-- 关于页内容（对齐旧前端 web_about.html；版本号已统一在首页导航栏展示，此处不再重复） -->
        <div style="text-align: center; padding: 16px 20px;">
          <img src="/assets/icons/logo.png" alt="AI-GZT" style="width: 96px; height: 96px; margin-bottom: 16px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);" />
          <div style="font-size: 24px; font-weight: 600; margin-bottom: 12px; color: #1f2329;">AI-GZT 桌面软件</div>
          <span style="display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 13px; color: #ffffff; background-color: #67C23A;">Windows 版本</span>
        </div>

        <div>
          <div style="font-size: 18px; font-weight: 600; margin-bottom: 12px; padding-left: 12px; border-left: 4px solid var(--primary); color: #1f2329;">工作台介绍</div>
          <p style="line-height: 1.8; color: #4e5969; margin-bottom: 12px;">
            AI工作台是一款本地化AI生产力辅助工具，集成多模型协作对话、本地代码知识库检索、多项目文件管理、插件扩展生态、定时任务调度等核心能力，所有数据均存储在本地，充分保障数据隐私安全。
          </p>
          <ul style="list-style: none; padding: 0; margin: 0;">
            <li style="padding: 6px 0; color: #4e5969; line-height: 1.6;">✅ 多轮AI对话，支持上下文记忆、文件上传解析、多模态能力扩展、多模型交互能力、可以实现复杂长任务执行</li>
            <li style="padding: 6px 0; color: #4e5969; line-height: 1.6;">✅ 本地RAG代码检索，基于gte-small-zh向量模型，精准定位项目代码片段</li>
            <li style="padding: 6px 0; color: #4e5969; line-height: 1.6;">✅ 内置智能文件编辑器，支持上百种开发格式、自动备份、AI辅助编辑</li>
            <li style="padding: 6px 0; color: #4e5969; line-height: 1.6;">✅ 插件扩展生态，内置 4 款实装插件（格式转换 / 信息采集 / 进程监控 / 安全编辑），并提供 3 类开发模板（AIGC 生成 / 信息采集查询 / 本地操作）按需扩展</li>
            <li style="padding: 6px 0; color: #4e5969; line-height: 1.6;">✅ 定时任务调度，支持周期性执行自定义任务、脚本、AI工作流</li>
            <li style="padding: 6px 0; color: #4e5969; line-height: 1.6;">✅ 内置浏览器、截图工具等实用工具，一站式提升开发效率</li>
          </ul>
        </div>

        <div>
          <div style="font-size: 18px; font-weight: 600; margin-bottom: 12px; padding-left: 12px; border-left: 4px solid var(--primary); color: #1f2329;">合规与帮助</div>
          <div style="display: flex; gap: 12px; flex-wrap: wrap;">
            <button type="button" style="height: 32px; padding: 0 16px; font-size: 14px; color: #1f2329; background-color: #ffffff; border: 1px solid #c9cdd4; border-radius: 4px; cursor: pointer;" @click="openExternal('/docs/third_party_licenses')">查看第三方开源声明</button>
            <button type="button" style="height: 32px; padding: 0 16px; font-size: 14px; color: #1f2329; background-color: #ffffff; border: 1px solid #c9cdd4; border-radius: 4px; cursor: pointer;" @click="openExternal('/docs/user_guide')">查看使用说明</button>
            <button type="button" style="height: 32px; padding: 0 16px; font-size: 14px; color: #1f2329; background-color: #ffffff; border: 1px solid #c9cdd4; border-radius: 4px; cursor: pointer;" @click="openExternal('https://gitee.com/chen-bohan3000/ai-gzt')">项目官网</button>
          </div>
        </div>

        <div>
          <div style="font-size: 18px; font-weight: 600; margin-bottom: 12px; padding-left: 12px; border-left: 4px solid var(--primary); color: #1f2329;">技术栈</div>
          <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            <span style="padding: 4px 12px; background-color: var(--primary-bg, #f2f3f5); color: var(--primary); border-radius: 4px; font-size: 13px;">Python 3.11</span>
            <span style="padding: 4px 12px; background-color: var(--primary-bg, #f2f3f5); color: var(--primary); border-radius: 4px; font-size: 13px;">PySide6</span>
            <span style="padding: 4px 12px; background-color: var(--primary-bg, #f2f3f5); color: var(--primary); border-radius: 4px; font-size: 13px;">FastAPI</span>
            <span style="padding: 4px 12px; background-color: var(--primary-bg, #f2f3f5); color: var(--primary); border-radius: 4px; font-size: 13px;">Vue 3</span>
            <span style="padding: 4px 12px; background-color: var(--primary-bg, #f2f3f5); color: var(--primary); border-radius: 4px; font-size: 13px;">Vite</span>
            <span style="padding: 4px 12px; background-color: var(--primary-bg, #f2f3f5); color: var(--primary); border-radius: 4px; font-size: 13px;">Transformers</span>
            <span style="padding: 4px 12px; background-color: var(--primary-bg, #f2f3f5); color: var(--primary); border-radius: 4px; font-size: 13px;">Sentence-Transformers</span>
            <span style="padding: 4px 12px; background-color: var(--primary-bg, #f2f3f5); color: var(--primary); border-radius: 4px; font-size: 13px;">FAISS</span>
            <span style="padding: 4px 12px; background-color: var(--primary-bg, #f2f3f5); color: var(--primary); border-radius: 4px; font-size: 13px;">PyInstaller</span>
            <span style="padding: 4px 12px; background-color: var(--primary-bg, #f2f3f5); color: var(--primary); border-radius: 4px; font-size: 13px;">Inno Setup</span>
            <span style="padding: 4px 12px; background-color: var(--primary-bg, #f2f3f5); color: var(--primary); border-radius: 4px; font-size: 13px;">SQLite</span>
            <span style="padding: 4px 12px; background-color: var(--primary-bg, #f2f3f5); color: var(--primary); border-radius: 4px; font-size: 13px;">APScheduler</span>
          </div>
        </div>

        <div style="text-align: center; margin-top: 16px; padding-top: 16px; border-top: 1px solid #ebeef5; color: #909399; font-size: 13px; line-height: 1.8;">
          <p>Copyright © 2026 AI工作台开发团队</p>
          <p>本产品遵循相关开源许可证协议，所有第三方组件版权均归原作者所有</p>
        </div>
      </div>
    </div>
  </div>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'

/** 打开外部链接/页面（对齐旧前端 web_about.html 的 window.open 行为） */
function openExternal(url: string) {
  window.open(url, '_blank')
}
</script>

<style scoped>
.box-div-2jblc {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-hwfxb {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  flex-grow: 1;
  min-height: 0px;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-lzyyr {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  min-height: 320px;
  flex-grow: 1;
  overflow: auto;
  background-color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding-top: 16px;
  padding-right: 16px;
  padding-bottom: 16px;
  padding-left: 16px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  border-bottom-left-radius: 8px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}
</style>
