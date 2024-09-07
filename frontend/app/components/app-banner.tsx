import type { FC } from 'react'
import React from 'react'
import AppIcon from '@/app/components/base/app-icon'
export type IHeaderProps = {
    title: string
    isMobile?: boolean
    onShowSideBar?: () => void
    onCreateNewChat?: () => void
}
const AppBanner: FC<IHeaderProps> = ({
    title,
}) => {
    return (
        <div className="flex items-center">
            <AppIcon size="medium" />
            <div className="ml-3 inline-block leading-3">
                <div className="text-sm leading-3">NanbyoSupportChat</div>
                <div className="text-lg font-bold">{title}</div>
            </div>
        </div>
    )
}

export default React.memo(AppBanner)
