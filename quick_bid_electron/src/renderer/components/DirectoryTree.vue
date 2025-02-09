<script setup>
import { ref } from 'vue'
import { Tree } from 'ant-design-vue'

// 简单版本的数据结构
const treeData = ref([
  {
    key: '1',
    title: '第一章 投标函',
    children: [
      { key: '1-1', title: '1.1 报价清单' }
    ]
  }
])

// 动态编号生成函数
const generateDisplayNumbers = (nodes) => {
  return nodes.map((node, index) => ({
    ...node,
    title: `${index + 1}. ${node.title}`,
    children: node.children ? generateDisplayNumbers(node.children) : []
  }))
}
</script>

<template>
  <a-tree
    :tree-data="generateDisplayNumbers(treeData)"
    draggable
    @drop="handleDrop"
    blockNode
  />
</template>
