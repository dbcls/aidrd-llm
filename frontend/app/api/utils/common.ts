import { type NextRequest } from 'next/server'
import { ChatClient, DifyClient } from 'dify-client'
import { v4 } from 'uuid'
import { KNOWLEDGE_API_KEY, API_KEY, API_URL, APP_ID } from '@/config'

const userPrefix = `user_${APP_ID}:`

export const getInfo = (request: NextRequest) => {
  const sessionId = request.cookies.get('session_id')?.value || v4()
  const user = userPrefix + sessionId
  return {
    sessionId,
    user,
  }
}

export const setSession = (sessionId: string) => {
  return { 'Set-Cookie': `session_id=${sessionId}` }
}

export const client = new ChatClient(API_KEY, API_URL || undefined)


export const knowledgeClient = new DifyClient(KNOWLEDGE_API_KEY, API_URL || undefined)


export const addTextFragments = (baseUrl: string, content: string) => {
    if (!baseUrl || baseUrl.includes('#')) {
        // すでにアンカーやテクストフラグメントが含まれている場合はそのまま返す
        return baseUrl
    }
    let fragments = content.split(/ |\n/)
    fragments = fragments.map(f => f.replaceAll('-', '').replaceAll("\r", "")) // Safariではハイフンが含まれるとリンクが正しく動作しないようなので削除する
    fragments = fragments.filter(f => f.length > 0)
    let urlWithTextFragments = `${baseUrl}#:~:text=${fragments.join('&text=')}`
    const MAX_URL_LENGTH = 4096
    if (urlWithTextFragments.length > MAX_URL_LENGTH) {
        urlWithTextFragments = urlWithTextFragments.slice(0, MAX_URL_LENGTH)
    }
    return urlWithTextFragments
}
