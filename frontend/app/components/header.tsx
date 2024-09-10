import type { FC } from 'react'
import React from 'react'
import Button from '@/app/components/base/button'
import {
  Bars3Icon,
  PencilSquareIcon,
} from '@heroicons/react/24/solid'
import AppBanner from '@/app/components/app-banner'
import { InputsProps } from './inputs'
import Inputs from './inputs'
import { SimpleTooltip } from './base/tooltip'


export type IHeaderProps = {
  title: string
  isMobile?: boolean
  showInputs?: boolean
  inputsProps?: InputsProps
  onShowSideBar?: () => void
  onCreateNewChat?: () => void
}
const Header: FC<IHeaderProps> = ({
  title,
  isMobile,
  onShowSideBar,
  inputsProps,
  showInputs = true,
  onCreateNewChat = null,
}) => {
  if (inputsProps) {
    inputsProps.inlineFlex = true
    inputsProps.showLabel = false
    inputsProps.className = '!p-3'
  }
  return (
    <div className="shrink-0 flex items-center justify-between h-16 px-3 bg-white border-b-2">
      <div className='flex items-center space-x-2'>
        <a href="/">
          <AppBanner title={title} />
        </a>


      </div>

      <div className="inline h-full">
        {showInputs && (
          <Inputs {...inputsProps}
          />)
        }
        {onCreateNewChat && (
          <Button
            onClick={onCreateNewChat}
            dataTooltipId='delete-tip'
            className="ml-5 my-auto">
            <span className="clear-icon mr-3" style={{ width: "13px", height: "18px" }}></span>
            <span className="border-b">
            </span>
            <SimpleTooltip
              selector='delete-tip'
              content='会話の消去'
            >
            </SimpleTooltip>
          </Button>

        )}
        <a data-tooltip-id='documents-tip' className="inline-flex items-center content-center px-4 mt-5" href="/documents">
          <img src="/icons/documents.png" style={{ height: "18px" }} ></img>
          <SimpleTooltip
            selector='documents-tip'
            content='根拠となる資料の一覧'
          >
          </SimpleTooltip>
        </a>
      </div>
    </div >
  )
}

export default React.memo(Header)
