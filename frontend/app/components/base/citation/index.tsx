import { useEffect, useMemo, useRef, useState } from 'react'
import type { FC } from 'react'
import { useTranslation } from 'react-i18next'
import s from './style.module.css'
import type { CitationItem } from '../type'

export type Resources = {
    documentId: string
    documentName: string
    dataSourceType: string
    urlWithTextFragments?: string,
    sources: CitationItem[]
}

type CitationProps = {
    data: CitationItem[]
    containerClassName?: string
}

/// ヒットしたセグメントの内容を元に、URLにテキストフラグメントを追加する
function addTextFragments(baseUrl: string, content: string) {
    if (baseUrl.includes('#')) {
        // すでにアンカーやテクストフラグメントが含まれている場合はそのまま返す
        return baseUrl
    }
    let fragments = content.split(/ |\n/)
    fragments = fragments.filter(f => f.length > 0)
    let urlWithTextFragments = `${baseUrl}#:~:text=${fragments.join('&text=')}`
    const MAX_URL_LENGTH = 4096
    if (urlWithTextFragments.length > MAX_URL_LENGTH) {
        urlWithTextFragments = urlWithTextFragments.slice(0, MAX_URL_LENGTH)
    }
    return urlWithTextFragments
}

const Citation: FC<CitationProps> = ({
    data,
    containerClassName = 'chat-answer-container',
}) => {
    const citeWithFragments = process.env.NEXT_PUBLIC_CITE_WITH_FRAGMENTS?.toLowerCase() === 'true'
    const { t } = useTranslation()
    const elesRef = useRef<HTMLDivElement[]>([])
    const [limitNumberInOneLine, setlimitNumberInOneLine] = useState(0)
    const [showMore, setShowMore] = useState(false)
    const resources = useMemo(() => data.reduce((prev: Resources[], next) => {
        const documentId = next.document_id
        const documentName = next.document_name
        const dataSourceType = next.data_source_type
        const documentIndex = prev.findIndex(i => i.documentId === documentId)
        const urlWithTextFragments = citeWithFragments ? addTextFragments(documentName, next.content) : ''

        if (documentIndex > -1) {
            prev[documentIndex].sources.push(next)
        }
        else {
            prev.push({
                documentId,
                documentName,
                urlWithTextFragments,
                dataSourceType,
                sources: [next],
            })
        }

        return prev
    }, []), [data])


    return (
        <div className='-mb-1 -mt-3 ml-2 bg-slate-200 rounded-b-2xl rounded-lr-2xl'>
            <div className='relative flex pl-4'>
                <span className="mr-3 mt-5">引用:</span>
                <div className="inline-block my-3">
                    {
                        resources.map((res, index) => (
                            <a
                                class={`${s.citationLink}` + " block rounded-full bg-white my-2 py-1 px-3"}

                                href={res.urlWithTextFragments || res.documentName} target="_blank">
                                {res.documentName}
                            </a>
                        ))
                    }
                </div>
            </div>
        </div>
    )
}

export default Citation
