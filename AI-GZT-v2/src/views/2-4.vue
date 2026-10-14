<!--
  页面《2》　路由:/2-4（24）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <Layout4>
  <div class="box-div-gtt7h">
    <div class="box-div-gp5nv">
      <div class="box-div-rq2dh">
        <div class="box-div-p9k4y">
          <h2 class="box-h2-v4d5o">界面主题</h2>
          <button class="box-button-21a1q" type="submit" @click="saveConfig">保存配置</button>
        </div>
        <div class="box-div-zfhzw">
          <p class="box-p-ozebc">主题主色</p>
          <input class="box-input-7wsri" type="text" placeholder="请输入内容" v-model="config.theme_primary_color" />
        </div>
        <div class="box-div-138pe">
          <p class="box-p-nt5ps">配色预设</p>
          <button class="box-button-0xsmx" type="submit" @click="applyPreset('classic')">经典白蓝</button>
          <button class="box-button-uolzp" type="submit" @click="applyPreset('pinkpurple')">微粉紫</button>
          <button class="box-button-k67w3" type="submit" @click="applyPreset('cyan')">微蓝青</button>
          <button class="box-button-eo2cy" type="submit" @click="applyPreset('softpink')">微微粉</button>
        </div>
        <div class="box-div-crong">
          <h2 class="box-h2-lm5xz">运行设置</h2>
        </div>
        <div class="box-div-i8ws9">
          <p class="box-p-rybw1">显示调试控制台</p>
          <div
            class="box-div-wjcx6"
            @click="config.show_debug_console = !config.show_debug_console"
            :style="{ justifyContent: config.show_debug_console ? 'flex-end' : 'flex-start', backgroundColor: config.show_debug_console ? 'var(--primary)' : '#c9cdd4' }"
          >
            <div class="box-div-jgb0g"></div>
          </div>
          <p class="box-p-eq6e0">可开启查看实时运行日志，保存后重启生效</p>
        </div>
      </div>
    </div>
  </div>
  </Layout4>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { get, post } from '@/api/request'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'
import Layout4 from '@/layouts/Layout4.vue'

// 界面主题配置（与后端 config.json 字段对应）
const config = ref<Record<string, any>>({
  theme_primary_color: '#165DFF',
  show_debug_console: true,
})

// 配色预设（色值口径与 web_settings.html 保持一致）
const presets: Record<string, string> = {
  classic: '#165DFF',
  pinkpurple: '#7C4DFF',
  cyan: '#0D8F8F',
  softpink: '#EE2AF1',
}

// 一键套用预设主色（仅改本地值，保存后由后端热更新外壳样式）
function applyPreset(name: string) {
  const color = presets[name]
  if (color) config.value.theme_primary_color = color
  // 【主题统一·L1-③ 断点2 修复】点预设按钮 → 立即调用 ThemeKit 实时预览:
  // 原实现只改本地 config.value，页面颜色不变，必须"保存配置"才生效（体验割裂）。
  // setPrimary(color) 会派生 hover/active/light/bg 等色阶并写入 :root 内联 style，
  // 由于内联 style 优先级高于 CSS 内 var() 引用，所有接令牌的地方（按钮/用户气泡/系统派发蓝字等）立刻跟随。
  // 用 (window as any) 绕过 vue-tsc 类型检查（ThemeKit 由 /static/theme.js 运行时挂载，TS 无声明）；
  // 用 ?. 可选调用，保证 theme.js 未加载时也不抛错（静默降级）。
  if (color) (window as any).ThemeKit?.setPrimary(color)
}

// 加载系统配置
async function loadConfig() {
  try {
    const data = await get<Record<string, any>>('/api/config/get')
    if (data) {
      config.value = { ...config.value, ...data }
    }
  } catch (e) {
    console.error('加载系统配置失败:', e)
  }
}

// 保存系统配置（提交完整 config，避免嵌套子对象被浅合并覆盖；后端对主题主色做热更新）
async function saveConfig() {
  try {
    await post('/api/config/set', { config: config.value })
    // 【主题统一·L1-④ 断点3 修复】保存成功后当前页立即生效:
    // 原实现只 POST 到后端，当前页颜色不变，要等 theme.js 的 4 秒跨窗轮询或手动刷新才生效。
    // setTheme({primary,bgPage,bgCard}) 一次性应用主色+界面底色+卡片底色，且会把主题写回
    // localStorage（theme.js init 内的缓存回写逻辑），下次刷新首屏也不闪。
    // 同 L1-③:用 (window as any) + ?. 兼容 vue-tsc 类型检查与 theme.js 未加载场景。
    ;(window as any).ThemeKit?.setTheme({ primary: config.value.theme_primary_color })
    console.log('界面主题配置保存成功')
  } catch (e) {
    console.error('保存界面主题配置失败:', e)
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.box-div-gtt7h {
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

.box-div-gp5nv {
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

.box-div-rq2dh {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 40px;
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
  flex-grow: 1;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-div-p9k4y {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  justify-content: space-between;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-h2-v4d5o {
  font-size: 20px;
  font-weight: 600;
  color: #1f2329;
  line-height: 1.4;
  margin-top: 0;
  margin-bottom: 0;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-21a1q {
  height: 32px;
  font-size: 14px;
  color: #ffffff;
  background-color: var(--primary);
  border-style: none;
  padding-top: 6px;
  padding-right: 16px;
  padding-bottom: 6px;
  padding-left: 16px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-zfhzw {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-ozebc {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-input-7wsri {
  width: 146px;
  height: 32px;
  font-size: 14px;
  color: #1f2329;
  background-color: #ffffff;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-style: solid;
  border-color: #c9cdd4;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-138pe {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-nt5ps {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-0xsmx {
  height: 32px;
  font-size: 14px;
  color: #ffffff;
  background-color: var(--primary);
  border-style: none;
  padding-top: 6px;
  padding-right: 16px;
  padding-bottom: 6px;
  padding-left: 16px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-uolzp {
  height: 32px;
  font-size: 14px;
  color: #ffffff;
  background-color: var(--primary);
  border-style: none;
  padding-top: 6px;
  padding-right: 16px;
  padding-bottom: 6px;
  padding-left: 16px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-k67w3 {
  height: 32px;
  font-size: 14px;
  color: #ffffff;
  background-color: var(--primary);
  border-style: none;
  padding-top: 6px;
  padding-right: 16px;
  padding-bottom: 6px;
  padding-left: 16px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-eo2cy {
  height: 32px;
  font-size: 14px;
  color: #ffffff;
  background-color: var(--primary);
  border-style: none;
  padding-top: 6px;
  padding-right: 16px;
  padding-bottom: 6px;
  padding-left: 16px;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
  border-bottom-left-radius: 4px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-crong {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  justify-content: space-between;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-h2-lm5xz {
  font-size: 20px;
  font-weight: 600;
  color: #1f2329;
  line-height: 1.4;
  margin-top: 0;
  margin-bottom: 0;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-i8ws9 {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-rybw1 {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 134px;
  display: flex;
  justify-content: flex-end;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-wjcx6 {
  display: flex;
  flex-direction: row;
  justify-content: flex-end;
  align-items: center;
  width: 44px;
  height: 24px;
  min-width: 44px;
  padding-left: 4px;
  padding-right: 4px;
  background-color: var(--primary);
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
  border-bottom-right-radius: 12px;
  border-bottom-left-radius: 12px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-div-jgb0g {
  width: 16px;
  height: 16px;
  min-width: 16px;
  max-width: 16px;
  background-color: #ffffff;
  border-top-left-radius: 50%;
  border-top-right-radius: 50%;
  border-bottom-right-radius: 50%;
  border-bottom-left-radius: 50%;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
  gap: 8px;
}

.box-p-eq6e0 {
  font-size: 12px;
  color: #9298a0;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  width: 360px;
  display: flex;
  justify-content: flex-start;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}
</style>
