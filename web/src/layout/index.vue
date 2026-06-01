<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="layout-aside">
      <div class="logo">
        <span class="logo-icon">📋</span>
        <span class="logo-text">QuickBid</span>
        <span class="logo-version">v3</span>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/projects">
          <el-icon><FolderOpened /></el-icon>
          <span>项目管理</span>
        </el-menu-item>
        <el-menu-item index="/materials">
          <el-icon><Document /></el-icon>
          <span>材料库</span>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <span class="status-dot" />
        <span class="status-text">系统就绪</span>
      </div>
    </el-aside>
    <el-container>
      <el-header class="layout-header">
        <span class="header-title">标书制作工具</span>
        <span class="header-subtitle">确认驱动对话 · 多 Agent 协作</span>
      </el-header>
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { FolderOpened, Document } from '@element-plus/icons-vue'
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

/* ---- Sidebar ---- */
.layout-aside {
  background: var(--qb-surface);
  border-right: 1px solid var(--qb-border);
  display: flex;
  flex-direction: column;
}

.logo {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 8px;
  border-bottom: 1px solid var(--qb-border);
}
.logo-icon { font-size: 20px; }
.logo-text {
  font-family: var(--qb-font-mono);
  font-size: 18px;
  font-weight: 600;
  color: var(--qb-primary);
}
.logo-version {
  font-family: var(--qb-font-mono);
  font-size: 11px;
  color: var(--qb-text-secondary);
  background: var(--qb-bg);
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: auto;
}

.sidebar-menu {
  border-right: none;
  flex: 1;
  padding-top: 8px;
}

.sidebar-menu .el-menu-item {
  font-family: var(--qb-font-body);
  font-size: 14px;
  height: 44px;
  line-height: 44px;
  margin: 2px 8px;
  border-radius: var(--qb-radius);
}
.sidebar-menu .el-menu-item.is-active {
  background: rgba(37, 99, 235, 0.08);
  color: var(--qb-primary);
  font-weight: 500;
}

.sidebar-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--qb-border);
  display: flex;
  align-items: center;
  gap: 8px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--qb-success);
}
.status-text {
  font-size: 12px;
  color: var(--qb-text-secondary);
}

/* ---- Header ---- */
.layout-header {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 56px;
  background: var(--qb-surface);
  border-bottom: 1px solid var(--qb-border);
  padding: 0 24px;
}
.header-title {
  font-family: var(--qb-font-mono);
  font-size: 16px;
  font-weight: 600;
  color: var(--qb-text);
}
.header-subtitle {
  font-size: 13px;
  color: var(--qb-text-secondary);
}

/* ---- Main ---- */
.layout-main {
  background: var(--qb-bg);
  padding: 24px;
  min-height: 0;
}
</style>
