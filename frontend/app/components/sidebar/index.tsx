import React from 'react'
import type { FC } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChatBubbleOvalLeftEllipsisIcon,
  PencilSquareIcon,
} from '@heroicons/react/24/outline'
import { ChatBubbleOvalLeftEllipsisIcon as ChatBubbleOvalLeftEllipsisSolidIcon } from '@heroicons/react/24/solid'
import Button from '@/app/components/base/button'
import Inputs from '@/app/components/inputs'
import { InputsProps } from '@/app/components/inputs'
// import Card from './card'
import type { ConversationItem } from '@/types/app'

function classNames(...classes: any[]) {
  return classes.filter(Boolean).join(' ')
}

const MAX_CONVERSATION_LENTH = 20

export type ISidebarProps = {
  copyRight: string
  hasSetInputs: boolean
  currentId: string
  onCurrentIdChange: (id: string) => void
  list: ConversationItem[],
  inputsProps: InputsProps
}

const Sidebar: FC<ISidebarProps> = ({
  copyRight,
  hasSetInputs,
  currentId,
  onCurrentIdChange,
  list,
  inputsProps: { setInputs, inputs, promptConfig }
}) => {
  const { t } = useTranslation()
  return (
    <div
      className="shrink-0 flex flex-col overflow-y-auto bg-white pc:w-[300px] tablet:w-[300px] mobile:w-[300px]  border-r border-gray-200 tablet:h-[calc(100vh_-_3rem)] mobile:h-screen"
    >
      <div className="flex flex-shrink-0 p-4 !pb-0">
        <Button
          onClick={() => { onCurrentIdChange('-1'); }}
          className="group block w-full flex-shrink-0 !justify-start !h-9 text-primary-600 items-center text-sm">
          <PencilSquareIcon className="mr-2 h-4 w-4" /> 会話内容のクリア
        </Button>
      </div>

      {hasSetInputs && <Inputs
        setInputs={setInputs}
        inputs={inputs}
        promptConfig={promptConfig}
      />}
      <ul style={{ listStyleType: 'disc', paddingLeft: '20px' }}>
        <li>
          チャットのログはサーバに保存されます。プライバシー保護のため、個人情報の入力は避けてください。
        </li>
        <li>
          このチャットボットが提供する情報は参考用です。間違いが含まれる可能性があるため、必ず元の情報源を確認してください。
        </li>
      </ul>
      {/* <a className="flex flex-shrink-0 p-4" href="https://langgenius.ai/" target="_blank">
        <Card><div className="flex flex-row items-center"><ChatBubbleOvalLeftEllipsisSolidIcon className="text-primary-600 h-6 w-6 mr-2" /><span>LangGenius</span></div></Card>
      </a> */}
      {/* <div className="flex flex-shrink-0 pr-4 pb-4 pl-4">
        <div className="text-gray-400 font-normal text-xs">© {copyRight} {(new Date()).getFullYear()}</div>
      </div> */}
    </div>
  )
}

export default React.memo(Sidebar)
