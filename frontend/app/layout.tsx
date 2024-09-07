import { getLocaleOnServer } from '@/i18n/server'

import './styles/globals.css'
import { Zen_Maru_Gothic } from "next/font/google"
import './styles/markdown.scss'

const zenMaruGothic = Zen_Maru_Gothic({ subsets: ["latin"], weight: ["300", "400", "500", "700", "900"] })

const LocaleLayout = ({
  children,
}: {
  children: React.ReactNode
}) => {
  const locale = getLocaleOnServer()
  return (
    <html lang={locale ?? 'en'} className="h-full">
      <body className={"h-full " + zenMaruGothic.className}>
        <div>
          <div className="w-screen h-screen min-w-[300px]">
            {children}
          </div>
        </div>
      </body>
    </html>
  )
}

export default LocaleLayout
