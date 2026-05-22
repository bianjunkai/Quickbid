<template>
  <el-container class="layout-container">
    <el-aside width="200px">
      <div class="logo">QuickBid</div>
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
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-title">标书制作工具</div>
      </el-header>
      <el-main>
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
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  font-size: 18px;
  font-weight: bold;
  color: #409eff;
  border-bottom: 1px solid #e6e6e6;
}
.sidebar-menu {
  border-right: none;
}
.el-header {
  display: flex;
  align-items: center;
  border-bottom: 1px solid #e6e6e6;
}
.header-title {
  font-size: 16px;
  font-weight: 600;
}
</style>
