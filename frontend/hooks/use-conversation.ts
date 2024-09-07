import { useState } from 'react'
import produce from 'immer'
import { useGetState } from 'ahooks'
import type { ChatItem } from '@/types/app'
import type { ConversationItem } from '@/types/app'

const storageConversationIdKey = 'conversationIdInfo'
const storageInputsKey = 'conversationInputs'
const chatListKey = 'chatList'

type ConversationInfoType = Omit<ConversationItem, 'inputs' | 'id'>
function useConversation() {
  const [conversationList, setConversationList] = useState<ConversationItem[]>([])
  const [currConversationId, doSetCurrConversationId, getCurrConversationId] = useGetState<string>('-1')
  // when set conversation id, we do not have set appId
  const setCurrConversationId = (id: string, appId: string, isSetToLocalStroge = true, newConversationName = '') => {
    doSetCurrConversationId(id)
    if (isSetToLocalStroge) {
      // conversationIdInfo: {[appId1]: conversationId1, [appId2]: conversationId2}
      const conversationIdInfo = globalThis.localStorage?.getItem(storageConversationIdKey) ? JSON.parse(globalThis.localStorage?.getItem(storageConversationIdKey) || '') : {}
      conversationIdInfo[appId] = id
      globalThis.localStorage?.setItem(storageConversationIdKey, JSON.stringify(conversationIdInfo))
    }
  }

  const getConversationIdFromStorage = (appId: string) => {
    const conversationIdInfo = globalThis.localStorage?.getItem(storageConversationIdKey) ? JSON.parse(globalThis.localStorage?.getItem(storageConversationIdKey) || '') : {}
    const id = conversationIdInfo[appId]
    return id
  }

  const isNewConversation = currConversationId === '-1'
  const [currInputs, setCurrInputs] = useState<Record<string, any> | null>(null)

  const setCurrInputsIntoLocalStorage = (inputs: Record<string, any> | null) => {
    globalThis.localStorage?.setItem(storageInputsKey, JSON.stringify(inputs))
    setCurrInputs(inputs)
  }

  const getInputsFromLocalStorage = () => {
    const inputs = globalThis.localStorage?.getItem(storageInputsKey) ? JSON.parse(globalThis.localStorage?.getItem(storageInputsKey) || '') : {}
    return inputs
  }

  // info is muted
  const [newConversationInfo, setNewConversationInfo] = useState<ConversationInfoType | null>(null)
  const [existConversationInfo, setExistConversationInfo] = useState<ConversationInfoType | null>(null)
  const currConversationInfo = isNewConversation ? newConversationInfo : existConversationInfo

  const [chatList, setChatListInternal, getChatList] = useGetState<ChatItem[]>([])

  const setChalListToLocalStorage = (list: ChatItem[]) => {
    globalThis.localStorage?.setItem(chatListKey, JSON.stringify(list))
    setChatListInternal(list)
  }


  const getChatListFromLocalStorage = () => {
    const list = globalThis.localStorage?.getItem(chatListKey) ? JSON.parse(globalThis.localStorage?.getItem(chatListKey) || '') : []
    return list
  }

  return {
    chatList,
    setChatList: setChalListToLocalStorage,
    getChatList,
    getChatListFromLocalStorage,
    conversationList,
    setConversationList,
    currConversationId,
    getCurrConversationId,
    setCurrConversationId,
    getConversationIdFromStorage,
    isNewConversation,
    currInputs,
    getInputsFromLocalStorage,
    setCurrInputs: setCurrInputsIntoLocalStorage,
    currConversationInfo,
    setNewConversationInfo,
    setExistConversationInfo,
  }
}

export default useConversation
