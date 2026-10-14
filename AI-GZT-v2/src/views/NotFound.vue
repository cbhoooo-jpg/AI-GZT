<template>
  <div class="nf-wrap">
    <h1 class="nf-code">404</h1>
    <p class="nf-text">页面不存在或已被移除</p>
    <router-link class="nf-btn" to="/">返回首页</router-link>
  </div>
</template>

<script setup lang="ts">
// 内置 404 页:由低代码平台生成，与 src/router/draft.ts 的通配兜底路由配套。
</script>

<style scoped>
.nf-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  gap: 12px;
  padding: 32px;
}
.nf-code {
  margin: 0;
  font-size: 84px;
  font-weight: 700;
  color: #c0c4cc;
  line-height: 1;
}
.nf-text {
  margin: 0;
  font-size: 16px;
  color: #606266;
}
.nf-btn {
  display: inline-block;
  padding: 8px 20px;
  border-radius: 4px;
  background: #1677ff;
  color: #ffffff;
  text-decoration: none;
  font-size: 14px;
}
.nf-btn:hover {
  background: #0958d9;
}
</style>
