'use client'
import React from 'react'
import useConversation from '@/hooks/use-conversation'
import Inputs from '@/app/components/inputs'
import { useEffect, useState } from 'react'
import { userInputsFormToPromptVariables } from '@/utils/prompt'
import { fetchAppParams, fetchKnowledgeList, fetchKnowledgeDocumentList } from '@/service'
import { UserInputFormItem } from '@/types/app'
import s from './style.module.css'
import Papa from 'papaparse';


const DocumentList = () => {
    const {
        getInputsFromLocalStorage,
    } = useConversation()

    const [promptVariables, setPromptVariables] = useState<UserInputFormItem[] | null>([])
    const [prefecture, setPrefecture] = useState<string | null>(null)
    const [currInputs, setCurrInputs] = useState<Record<string, any> | null>(null)
    const [documents, setDocuments] = useState<any[]>([])
    const [knowledgeIdDict, setKnowledgeIdDict] = useState<Record<string, any>>({})
    const [knowledgePortalDict, setKnowledgePortalDict] = useState<Record<string, any>>({})

    let inited = false

    useEffect(() => {
        if (inited) {
            return
        }
        (async () => {

            const appParams = await fetchAppParams()
            // fetch new conversation info
            const { user_input_form, opening_statement: introduction, file_upload, system_parameters }: any = appParams
            setPromptVariables(userInputsFormToPromptVariables(user_input_form))
            const storedInputs = getInputsFromLocalStorage()
            const prefecture = storedInputs?.prefecture
            if (prefecture) {
                setPrefecture(prefecture)
            }
            setCurrInputs(storedInputs)

            const knowledgeList = await fetchKnowledgeList() as Record<string, any>
            const dict: Record<string, any> = {}
            for (const knowledge of knowledgeList.data) {
                dict[knowledge.name] = knowledge.id
            }
            setKnowledgeIdDict(dict)
            if (prefecture && prefecture in dict) {
                const knowledgeId = dict[prefecture]
                const documentList = await fetchKnowledgeDocumentList(knowledgeId)
                setDocuments(documentList)
            }

            const portalCsv = await fetch("/prefecture_portal_url.csv")
            const portalCsvText = await portalCsv.text()
            const results = Papa.parse(portalCsvText, { header: true });
            const portalDict: Record<string, any> = {}
            for (const result of results.data) {
                portalDict[result.prefecture] = result.portal_url
            }
            setKnowledgePortalDict(portalDict)
        })()
        inited = true
    }
        ,
        []
    )

    const setPrefectureFromInputs = (inputs: Record<string, any>) => {
        setPrefecture(inputs?.prefecture)
        currInputs.prefecture = inputs?.prefecture
        setCurrInputs(currInputs)
        if (inputs?.prefecture && inputs.prefecture in knowledgeIdDict) {
            const knowledgeId = knowledgeIdDict[inputs.prefecture]
            setDocuments([]);
            (async () => {
                const documentList = await fetchKnowledgeDocumentList(knowledgeId)
                setDocuments(documentList)
            })()
        }
    }

    const promptConfig = {
        prompt_template: "",
        prompt_variables: promptVariables || []
    }

    let prefecturePortal = ""

    if (prefecture) {
        prefecturePortal = knowledgePortalDict[prefecture] || ""
    }

    const renderDocuments = () => {
        return (
            <div>
                {documents.length === 0 && "資料のロード中です..."}
                {documents.length !== 0 && (
                    <ul className={s.documentList}>
                        {documents.map((doc) => (
                            <li key={doc.id}>
                                <a href={doc.name} target="_blank">{doc.name}</a>
                            </li>
                        ))}
                    </ul>)
                }
            </div>)
    }
    return (
        <div>
            <div className="px-[58px] py-[25px]">
                <h1 className={s.headerWithBorder}>難病支援制度の根拠資料一覧</h1>
                <Inputs
                    setInputs={setPrefectureFromInputs}
                    inputs={currInputs}
                    promptConfig={promptConfig}
                />
                <span className="pl-4">
                    ポータルURL：<a href={prefecturePortal} target="_blank">
                        {prefecturePortal}
                    </a>
                </span>
                <h1 className={s.headerWithBorder + " mt-[40px]"}>関連資料</h1>
                {prefecture && (
                    renderDocuments()
                )}
            </div>
        </div >
    );
};

export default DocumentList;