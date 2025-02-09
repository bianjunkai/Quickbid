import { app, BrowserWindow, ipcMain } from 'electron'

ipcMain.handle('save-project', async (event, projectData) => {
  // 临时示例：保存到本地临时文件
  const fs = require('fs/promises')
  await fs.writeFile('temp.json', JSON.stringify(projectData))
  return { success: true }
})

ipcMain.handle('load-project', async () => {
  const data = await fs.readFile('temp.json', 'utf-8')
  return JSON.parse(data)
})

const saveProject = async () => {
    await window.electronAPI.saveProject(projectData.value)
  }