// 路由草稿:由低代码平台生成，仅含静态路由骨架
// [AI-FILL] 路由守卫 / 权限校验需在此补全（懒加载与 404 兜底已内置）
// 阶段1（前端重构 · 决策C①）:统一改为 Hash 模式历史 —— 详见文件末尾 createRouter 处注释
import { createRouter, createWebHashHistory } from 'vue-router'

export const routes = [
  // 默认进入首页
  { path: '/', redirect: '/page-o0x2f' },
  {
    path: '/page-o0x2f',
    name: 'pageO0x2f',
    component: () => import('@/views/PageO0x2f.vue'),
    meta: { title: '首页', isHome: true },
  },
  {
    path: '/1',
    name: '1',
    component: () => import('@/views/1.vue'),
    meta: { title: '1' },
  },
  {
    path: '/2',
    name: '2',
    component: () => import('@/views/2.vue'),
    meta: { title: '2' },
  },
  {
    path: '/3',
    name: '3',
    component: () => import('@/views/3.vue'),
    meta: { title: '3' },
  },
  {
    path: '/4',
    name: '4',
    component: () => import('@/views/4.vue'),
    meta: { title: '4' },
  },
  {
    path: '/5',
    name: '5',
    component: () => import('@/views/5.vue'),
    meta: { title: '5' },
  },
  {
    path: '/6',
    name: '6',
    component: () => import('@/views/6.vue'),
    meta: { title: '6' },
  },
  {
    path: '/7',
    name: '7',
    component: () => import('@/views/7.vue'),
    meta: { title: '7' },
  },
  {
    path: '/8',
    name: '8',
    component: () => import('@/views/8.vue'),
    meta: { title: '8' },
  },
  {
    path: '/9',
    name: '9',
    component: () => import('@/views/9.vue'),
    meta: { title: '9' },
  },
  {
    path: '/10',
    name: '10',
    component: () => import('@/views/10.vue'),
    meta: { title: '10' },
  },
  {
    path: '/1-2',
    name: '12',
    component: () => import('@/views/1-2.vue'),
    meta: { title: '1' },
  },
  {
    path: '/2-2',
    name: '22',
    component: () => import('@/views/2-2.vue'),
    meta: { title: '2' },
  },
  {
    path: '/3-2',
    name: '32',
    component: () => import('@/views/3-2.vue'),
    meta: { title: '3' },
  },
  {
    path: '/4-2',
    name: '42',
    component: () => import('@/views/4-2.vue'),
    meta: { title: '4' },
  },
  {
    path: '/5-2',
    name: '52',
    component: () => import('@/views/5-2.vue'),
    meta: { title: '5' },
  },
  {
    path: '/6-2',
    name: '62',
    component: () => import('@/views/6-2.vue'),
    meta: { title: '6' },
  },
  {
    path: '/7-2',
    name: '72',
    component: () => import('@/views/7-2.vue'),
    meta: { title: '7' },
  },
  {
    path: '/1-3',
    name: '13',
    component: () => import('@/views/1-3.vue'),
    meta: { title: '1' },
  },
  {
    path: '/2-3',
    name: '23',
    component: () => import('@/views/2-3.vue'),
    meta: { title: '2' },
  },
  {
    path: '/3-3',
    name: '33',
    component: () => import('@/views/3-3.vue'),
    meta: { title: '3' },
  },
  {
    path: '/4-3',
    name: '43',
    component: () => import('@/views/4-3.vue'),
    meta: { title: '4' },
  },
  {
    path: '/5-3',
    name: '53',
    component: () => import('@/views/5-3.vue'),
    meta: { title: '5' },
  },
  {
    path: '/6-3',
    name: '63',
    component: () => import('@/views/6-3.vue'),
    meta: { title: '6' },
  },
  {
    path: '/7-3',
    name: '73',
    component: () => import('@/views/7-3.vue'),
    meta: { title: '7' },
  },
  {
    path: '/8-2',
    name: '82',
    component: () => import('@/views/8-2.vue'),
    meta: { title: '8' },
  },
  {
    path: '/1-4',
    name: '14',
    component: () => import('@/views/1-4.vue'),
    meta: { title: '1' },
  },
  {
    path: '/2-4',
    name: '24',
    component: () => import('@/views/2-4.vue'),
    meta: { title: '2' },
  },
  {
    path: '/3-4',
    name: '34',
    component: () => import('@/views/3-4.vue'),
    meta: { title: '3' },
  },
  {
    path: '/1-5',
    name: '15',
    component: () => import('@/views/1-5.vue'),
    meta: { title: '1' },
  },
  {
    path: '/2-5',
    name: '25',
    component: () => import('@/views/2-5.vue'),
    meta: { title: '2' },
  },
  {
    path: '/1-6',
    name: '16',
    component: () => import('@/views/1-6.vue'),
    meta: { title: '1' },
  },
  {
    path: '/2-6',
    name: '26',
    component: () => import('@/views/2-6.vue'),
    meta: { title: '2' },
  },
  {
    path: '/3-5',
    name: '35',
    component: () => import('@/views/3-5.vue'),
    meta: { title: '3' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { title: '页面不存在' },
  },
]

export default createRouter({
  // 阶段1（前端重构 · 决策C①）:History 模式 → Hash 模式。
  //  —— History 模式下 URL 形如 /webapp/3，F5 刷新会向服务端请求该真实路径，
  //     FastAPI 未配置 catch-all 回退时会返回 404；
  //  —— Hash 模式下 URL 形如 /webapp/#/3，# 之后的部分不发送给服务端，
  //     F5 刷新始终请求 /webapp/ 本身，无需任何后端回退配置即可正常工作。
  history: createWebHashHistory(),
  routes,
})
