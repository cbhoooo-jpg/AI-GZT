<!--
  外壳页《首页》的公共 Layout 组件（第 65 批 B1 抽出）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
  本组件为公共外壳，被其子页以 <PageO0x2f> 包裹使用（出口位置 <slot /> 承接子页内容）。
-->
<template>
  <div class="box-div-8ouzx">
    <div class="box-div-62xqx">
      <div class="box-div-yanfg">
        <img class="box-span-3ttij" src="/assets/icons/logo.png" />
        <span class="box-span-6kcox">AI-GZT</span>
        <button class="box-button-gvyw3" type="button" @click="goPagePageO0x2f()" :class="{ 'lc-nav-active': route.path === '/page-o0x2f' }">主对话</button>
        <button class="box-button-hyhye" type="button" @click="goPage1()" :class="{ 'lc-nav-active': route.path === '/1' }">次级对话</button>
        <button class="box-button-ebs5o" type="button" @click="goPage2()" :class="{ 'lc-nav-active': route.path === '/2' }">仓库</button>
        <button class="box-button-lnrux" type="button" @click="goPage3()" :class="{ 'lc-nav-active': route.path === '/3' }">模型配置</button>
        <button class="box-button-poots" type="button" @click="goPage4()" :class="{ 'lc-nav-active': route.path === '/4' }">系统配置</button>
        <button class="box-button-v4ho7" type="button" @click="goPage5()" :class="{ 'lc-nav-active': route.path === '/5' }">备份</button>
        <button class="box-button-wr90q" type="button" @click="goPage6()" :class="{ 'lc-nav-active': route.path === '/6' }">日志</button>
        <button class="box-button-0ihym" type="button" @click="goPage7()" :class="{ 'lc-nav-active': route.path === '/7' }">任务</button>
        <button class="box-button-zjopk" type="button" @click="goPage8()" :class="{ 'lc-nav-active': route.path === '/8' }">插件</button>
        <button class="box-button-e327z" type="button" @click="goPage9()" :class="{ 'lc-nav-active': route.path === '/9' }">记忆</button>
        <button class="box-button-71sid" type="button" @click="goPage10()" :class="{ 'lc-nav-active': route.path === '/10' }">关于</button>
        <div class="box-div-2uaow">
          <p class="box-p-4xtqa">版本V2.0</p>
        </div>
      </div>
      <div class="box-div-35526"><slot /></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

/** 路由实例:由导航按钮的点击跳转使用（第 18 批自动生成） */
const router = useRouter()
/** 当前路由:由导航按钮的「当前页」高亮判定使用（第 69 批自动生成） */
const route = useRoute()

/** 第 18 批:导航按钮自动生成的页面跳转（导出即用，改交互时改此处） */
function goPagePageO0x2f() {
  router.push('/page-o0x2f')
}

function goPage1() {
  router.push('/1')
}

function goPage2() {
  router.push('/2')
}

function goPage3() {
  router.push('/3')
}

function goPage4() {
  router.push('/4')
}

function goPage5() {
  router.push('/5')
}

function goPage6() {
  router.push('/6')
}

function goPage7() {
  router.push('/7')
}

function goPage8() {
  router.push('/8')
}

function goPage9() {
  router.push('/9')
}

function goPage10() {
  router.push('/10')
}
</script>

<style scoped>
.box-div-8ouzx {
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

.box-div-62xqx {
  display: flex;
  flex-direction: row;
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

.box-div-yanfg {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 145px;
  min-height: 40px;
  background-color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding-top: 12px;
  padding-right: 12px;
  padding-bottom: 12px;
  padding-left: 12px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  border-bottom-left-radius: 8px;
  align-items: stretch;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-span-3ttij {
  font-size: 18px;
  color: #1d2129;
  align-self: center;
  height: 68px;
  width: auto;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-span-6kcox {
  font-size: 20px;
  font-weight: 600;
  color: #1d2129;
  text-align: center;
  margin-bottom: 12px;
  align-self: center;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-gvyw3 {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-hyhye {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-ebs5o {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-lnrux {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-poots {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-v4ho7 {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-wr90q {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-0ihym {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-zjopk {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-e327z {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-button-71sid {
  font-size: 14px;
  color: #4e5969;
  background-color: #ffffff;
  border-style: solid;
  padding-top: 6px;
  padding-right: 6px;
  padding-bottom: 6px;
  padding-left: 6px;
  width: 100%;
  text-align: center;
  border-top-width: 1px;
  border-right-width: 1px;
  border-bottom-width: 1px;
  border-left-width: 1px;
  border-color: #e5e6eb;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-2uaow {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  min-height: 40px;
  align-items: flex-end;
  justify-content: flex-end;
  margin-top: auto;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}

.box-p-4xtqa {
  font-size: 14px;
  color: #4e5969;
  line-height: 1.6;
  margin-top: 0;
  margin-bottom: 0;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  border-bottom-left-radius: 6px;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  gap: 8px;
}

.box-div-35526 {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 40px;
  background-color: #ffffff;
  box-shadow: none;
  padding-top: 0px;
  padding-right: 0px;
  padding-bottom: 0px;
  padding-left: 0px;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  border-bottom-left-radius: 8px;
  flex-grow: 1;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 14px;
}
</style>
