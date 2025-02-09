import axios from 'axios'

export class AIGenerator {
  constructor(apiKey) {
    this.client = axios.create({
      baseURL: 'https://api.deepseek.com/v1',
      headers: { 'Authorization': `Bearer ${apiKey}` }
    })
  }

  async generateContent(prompt, variables) {
    const finalPrompt = this.replaceVariables(prompt, variables)
    const response = await this.client.post('/chat/completions', {
      model: 'bid-expert-1.0',
      messages: [{ role: 'user', content: finalPrompt }]
    })
    return response.data.choices[0].message.content
  }

  // 简单变量替换（示例）
  replaceVariables(text, vars) {
    return Object.keys(vars).reduce((str, key) => {
      return str.replace(new RegExp(`{{${key}}}`, 'g'), vars[key])
    }, text)
  }
}
