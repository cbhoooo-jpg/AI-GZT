<!--
  页面《5》　路由:/5（5）
  项目:未命名项目　导出时间:2026-10-06T15:46:36.906Z
  [AI-FILL] 本文件为低代码平台生成的骨架，所有 [AI-FILL] 标记处需由 AI / 开发者补全真实逻辑。
-->
<template>
  <LayoutPageO0x2f>
  <div class="box-div-k4i3m">
    <div class="box-div-43opr">
      <div class="box-div-93r44">
        <div class="box-div-hbrve">
          <h2 class="box-h2-9f0jd">文件备份管理</h2>
          <button class="box-button-uz707" type="button" @click="saveBackupConfig">保存配置</button>
        </div>
        <div class="box-div-2eorn">
          <p class="box-p-upwxu">备份功能</p>
          <div class="box-div-wlsbt" :class="{ 'is-off': !backupConfig.enable_backup }" @click="backupConfig.enable_backup = !backupConfig.enable_backup">
            <div class="box-div-69qep"></div>
          </div>
          <p class="box-p-14eej">{{ backupConfig.enable_backup ? '已开启' : '已关闭' }}</p>
        </div>
        <div class="box-div-mqpx4">
          <p class="box-p-ifj09">保留天数</p>
          <input class="box-input-5cg01" type="number" min="1" max="365" v-model.number="backupConfig.retention_days" />
          <p class="box-p-e2zre">最大备份数</p>
          <input class="box-input-nwmld" type="number" min="10" max="10000" v-model.number="backupConfig.max_count" />
        </div>
        <div class="box-div-cft2b">
          <p class="box-p-6ledg"></p>
          <button class="box-button-lijl7" type="button" :disabled="!backupConfig.enable_backup" @click="fullBackup">全量备份</button>
          <button class="box-button-csvis" type="button" @click="loadBackupList">刷新列表</button>
          <button class="box-button-hgigt" type="button" @click="cleanBackup">清理过期</button>
          <button class="box-button-rj6ho" type="button" @click="cleanAllBackup">清空备份</button>
        </div>
        <div class="box-div-c9iuy">
          <div style="width: 100%;">
            <div style="text-align: right; margin-bottom: 8px; font-size: 12px; color: #909399;">共{{ backupList.length }}个备份文件</div>
            <div v-for="project in groupedBackupList" :key="project.projectName" class="bk-project">
              <div class="bk-project-title" @click="toggleProject(project.projectName)">
                {{ project.projectName }}（共{{ project.totalCount }}个备份）
              </div>
              <div v-show="activeCollapse.includes(project.projectName)">
                <div v-for="group in Object.values(project.fileGroups)" :key="group.original_path" class="bk-file">
                  <div class="bk-file-title" @click="toggleFile(project.projectName + '/' + group.original_path)">
                    {{ group.original_path }}（共{{ group.count }}个备份）
                  </div>
                  <div v-show="activeFileCollapse.includes(project.projectName + '/' + group.original_path)">
                    <div class="bk-toolbar">
                      <label class="bk-select-all">
                        <input class="bk-checkbox" type="checkbox" :checked="isGroupAllSelected(group)" @change="toggleGroupAll(group)" />
                        全选本文件
                      </label>
                      <button class="bk-btn bk-btn-batch" type="button" :disabled="selectedCount(group) === 0" @click="deleteSelectedBackups(group)">批量删除选中({{ selectedCount(group) }})</button>
                    </div>
                    <div v-for="item in group.list" :key="item.backup_file" class="bk-item">
                      <input class="bk-checkbox" type="checkbox" :checked="isSelected(item)" @change="toggleSelect(item)" />
                      <span class="bk-item-time">{{ item.backup_time }}</span>
                      <span class="bk-item-size">{{ item.file_size }}</span>
                      <span class="bk-item-restorable">{{ item.restorable ? '可恢复' : '不可恢复' }}</span>
                      <button class="bk-btn bk-btn-restore" type="button" :disabled="!item.restorable" @click="restoreBackup(item)">恢复</button>
                      <button class="bk-btn bk-btn-delete" type="button" @click="deleteBackup(item)">删除</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="backupList.length === 0" style="text-align: center; color: #999; padding: 40px 0;">暂无备份记录</div>
          </div>
        </div>
      </div>
    </div>
  </div>
  </LayoutPageO0x2f>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import LayoutPageO0x2f from '@/layouts/LayoutPageO0x2f.vue'
import { get, post } from '@/api/request'

/** 备份条目结构（与后端 /api/backup/list 返回项对齐） */
interface BackupItem {
  backup_file: string
  original_path: string
  backup_time: string
  file_size: string
  restorable: boolean
}

/** 备份配置结构（与后端 config.backup_config 对齐） */
interface BackupConfig {
  enable_backup: boolean
  retention_days: number
  max_count: number
}

/** 项目分组结构 */
interface ProjectGroup {
  projectName: string
  totalCount: number
  fileGroups: Record<string, { original_path: string; list: BackupItem[]; count: number }>
}

const backupList = ref<BackupItem[]>([])
const backupConfig = ref<BackupConfig>({
  enable_backup: true,
  retention_days: 30,
  max_count: 1000,
})
const activeCollapse = ref<string[]>([])
const activeFileCollapse = ref<string[]>([])
/** 已勾选的备份文件（存 backup_file，跨分组唯一，避免同名 key 冲突） */
const selectedBackups = ref<string[]>([])

/** 按「项目 → 文件」两级分组（对齐旧页 web_backup.html 的分组口径） */
const groupedBackupList = computed<ProjectGroup[]>(() => {
  const projectGroups: Record<string, ProjectGroup> = {}
  backupList.value.forEach((item) => {
    const cleanPath = (item.original_path || '').replace(/^仓库文件夹[\\/]/, '')
    const pathSegments = cleanPath.split(/[\\/]/)
    const projectName = pathSegments[0]
    const innerFilePath = pathSegments.slice(1).join('/')
    if (!projectGroups[projectName]) {
      projectGroups[projectName] = { projectName, totalCount: 0, fileGroups: {} }
    }
    if (!projectGroups[projectName].fileGroups[innerFilePath]) {
      projectGroups[projectName].fileGroups[innerFilePath] = {
        original_path: innerFilePath,
        list: [],
        count: 0,
      }
    }
    projectGroups[projectName].fileGroups[innerFilePath].list.push(item)
    projectGroups[projectName].fileGroups[innerFilePath].count += 1
    projectGroups[projectName].totalCount += 1
  })
  return Object.values(projectGroups).sort((a, b) =>
    a.projectName.localeCompare(b.projectName, 'zh-CN'),
  )
})

/** 加载备份配置（回填开关 / 保留天数 / 最大备份数） */
async function loadBackupConfig() {
  try {
    const data = await get<{ backup_config?: BackupConfig }>('/api/config/get')
    if (data && data.backup_config) backupConfig.value = data.backup_config
  } catch (e) {
    console.error('加载备份配置失败', e)
  }
}

/** 保存备份配置（先取全量配置，再回写 backup_config，避免覆盖其它配置项） */
async function saveBackupConfig() {
  try {
    const data = await get<Record<string, unknown>>('/api/config/get')
    const config = { ...(data || {}), backup_config: backupConfig.value }
    await post('/api/config/set', { config })
    window.alert('备份配置保存成功，即时生效！')
  } catch (e) {
    console.error('保存备份配置失败', e)
  }
}

/** 加载备份列表 */
async function loadBackupList() {
  try {
    const data = await get<BackupItem[]>('/api/backup/list')
    backupList.value = data || []
    // 刷新后清空已选中项，防止残留已被删除的 backup_file
    selectedBackups.value = []
  } catch (e) {
    console.error('加载备份列表失败', e)
  }
}

/** 恢复指定备份（恢复前系统会自动备份当前版本） */
async function restoreBackup(row: BackupItem) {
  if (!window.confirm(`确定要恢复备份文件【${row.original_path}】吗？恢复后当前文件会被覆盖，系统会自动备份当前版本`)) return
  try {
    await post('/api/backup/restore', { backup_file_name: row.backup_file })
    window.alert('恢复成功！')
    loadBackupList()
  } catch (e) {
    console.error('恢复失败', e)
  }
}

/** 全量备份所有项目文件 */
async function fullBackup() {
  if (!window.confirm('确定要执行全量文件备份吗？将备份当前所有项目文件到独立备份版本')) return
  try {
    await post('/api/backup/full')
    window.alert('全量备份完成')
    loadBackupList()
  } catch (e) {
    console.error('全量备份失败', e)
  }
}

/** 删除单个备份 */
async function deleteBackup(row: BackupItem) {
  if (!window.confirm(`确定要删除备份文件【${row.original_path}】吗？删除后无法恢复`)) return
  try {
    await post('/api/backup/delete', { backup_file_name: row.backup_file })
    window.alert('删除成功！')
    loadBackupList()
  } catch (e) {
    console.error('删除失败', e)
  }
}

/** 清理过期备份（按保留天数 + 最大备份数） */
async function cleanBackup() {
  if (!window.confirm(`确定要清理所有过期备份吗？将删除超过${backupConfig.value.retention_days}天或超过${backupConfig.value.max_count}个的最早备份`)) return
  try {
    await post('/api/backup/clean', {
      retention_days: backupConfig.value.retention_days,
      max_count: backupConfig.value.max_count,
    })
    window.alert('清理完成')
    loadBackupList()
  } catch (e) {
    console.error('清理失败', e)
  }
}

/** 清空全部备份（逐条删除，与旧页一致） */
async function cleanAllBackup() {
  if (!window.confirm('确定要清空所有备份文件吗？操作不可恢复，所有备份都会被永久删除')) return
  try {
    await Promise.all(
      backupList.value.map((item) =>
        post('/api/backup/delete', { backup_file_name: item.backup_file }),
      ),
    )
    window.alert(`已成功清空所有${backupList.value.length}个备份文件`)
    loadBackupList()
  } catch (e) {
    console.error('清空失败', e)
  }
}

/** 展开 / 收起项目分组 */
function toggleProject(name: string) {
  const idx = activeCollapse.value.indexOf(name)
  if (idx >= 0) activeCollapse.value.splice(idx, 1)
  else activeCollapse.value.push(name)
}

/** 展开 / 收起文件分组 */
function toggleFile(key: string) {
  const idx = activeFileCollapse.value.indexOf(key)
  if (idx >= 0) activeFileCollapse.value.splice(idx, 1)
  else activeFileCollapse.value.push(key)
}

/** 判断某条备份是否已勾选 */
function isSelected(item: BackupItem) {
  return selectedBackups.value.includes(item.backup_file)
}

/** 勾选 / 取消勾选单条备份 */
function toggleSelect(item: BackupItem) {
  const idx = selectedBackups.value.indexOf(item.backup_file)
  if (idx >= 0) selectedBackups.value.splice(idx, 1)
  else selectedBackups.value.push(item.backup_file)
}

/** 统计某「文件分组」内已勾选的条数（用于批量删除按钮上的数字） */
function selectedCount(group: { list: BackupItem[] }) {
  return group.list.filter((item) => selectedBackups.value.includes(item.backup_file)).length
}

/** 判断某「文件分组」是否已全选 */
function isGroupAllSelected(group: { list: BackupItem[] }) {
  return (
    group.list.length > 0 &&
    group.list.every((item) => selectedBackups.value.includes(item.backup_file))
  )
}

/** 「文件分组」级 全选 / 取消全选 */
function toggleGroupAll(group: { list: BackupItem[] }) {
  if (isGroupAllSelected(group)) {
    // 本组已全选 → 取消本组全部勾选
    group.list.forEach((item) => {
      const idx = selectedBackups.value.indexOf(item.backup_file)
      if (idx >= 0) selectedBackups.value.splice(idx, 1)
    })
  } else {
    // 本组未全选 → 补选本组全部（已选的不重复加入）
    group.list.forEach((item) => {
      if (!selectedBackups.value.includes(item.backup_file)) {
        selectedBackups.value.push(item.backup_file)
      }
    })
  }
}

/** 批量删除本「文件分组」内已勾选的备份（并发调用已有的单条删除接口，零新增后端） */
async function deleteSelectedBackups(group: { list: BackupItem[]; original_path: string }) {
  const targets = group.list.filter((item) => selectedBackups.value.includes(item.backup_file))
  if (targets.length === 0) return
  if (
    !window.confirm(
      `确定要删除【${group.original_path}】下选中的 ${targets.length} 个备份文件吗？删除后无法恢复`,
    )
  )
    return
  try {
    await Promise.all(
      targets.map((item) => post('/api/backup/delete', { backup_file_name: item.backup_file })),
    )
    window.alert(`已成功删除 ${targets.length} 个备份文件`)
    loadBackupList()
  } catch (e) {
    console.error('批量删除失败', e)
  }
}

onMounted(() => {
  loadBackupConfig()
  loadBackupList()
})
</script>

<style scoped>
.box-div-k4i3m {
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

.box-div-43opr {
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

.box-div-93r44 {
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

.box-div-hbrve {
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

.box-h2-9f0jd {
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

.box-button-uz707 {
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

.box-div-2eorn {
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

.box-p-upwxu {
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

.box-div-wlsbt {
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

.box-div-69qep {
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

.box-p-14eej {
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

.box-div-mqpx4 {
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

.box-p-ifj09 {
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

.box-input-5cg01 {
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

.box-p-e2zre {
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

.box-input-nwmld {
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

.box-div-cft2b {
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

.box-p-6ledg {
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

.box-button-lijl7 {
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

.box-button-csvis {
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

.box-button-hgigt {
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

.box-button-rj6ho {
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

.box-div-c9iuy {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  height: 320px;
  min-height: 0px;
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

/* ===== 备份开关「关」态（圆点靠左、底色转灰） ===== */
.box-div-wlsbt.is-off {
  background-color: #c9cdd4;
  justify-content: flex-start;
}

/* ===== 备份分组列表样式（对齐旧页 web_backup.html 的层级展示） ===== */
.bk-project {
  margin-bottom: 8px;
}
.bk-project-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2329;
  padding: 8px 10px;
  background: #f2f3f5;
  border-radius: 4px;
  cursor: pointer;
}
.bk-file {
  margin: 6px 0 0 12px;
}
.bk-file-title {
  font-size: 13px;
  color: #4e5969;
  padding: 6px 10px;
  background: #f7f8fa;
  border-radius: 4px;
  cursor: pointer;
}
.bk-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px 8px 22px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  color: #4e5969;
}
.bk-item-time {
  width: 180px;
}
.bk-item-size {
  width: 100px;
}
.bk-item-restorable {
  width: 80px;
}
.bk-btn {
  height: 26px;
  font-size: 12px;
  color: #ffffff;
  border-style: none;
  padding: 0 12px;
  border-radius: 4px;
  cursor: pointer;
}
.bk-btn-restore {
  background-color: var(--primary);
}
.bk-btn-delete {
  background-color: #f56c6c;
}
.bk-btn:disabled {
  background-color: #c9cdd4;
  cursor: not-allowed;
}

/* ===== 批量操作:工具栏 / 全选 / 复选框 / 批量删除按钮 ===== */
.bk-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px 6px 22px;
  background: #fafbfc;
  border-bottom: 1px dashed #ebeef5;
}
.bk-select-all {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #4e5969;
  cursor: pointer;
  user-select: none;
}
.bk-checkbox {
  width: 14px;
  height: 14px;
  margin: 0;
  cursor: pointer;
  accent-color: var(--primary);
}
.bk-btn-batch {
  background-color: #f56c6c;
}
</style>
