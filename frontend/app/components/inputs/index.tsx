'use client'

import type { FC } from 'react'
import React, { useEffect, useState } from 'react'
import s from './style.module.css'
import type { PromptConfig } from '@/types/app'
import Select from '@/app/components/base/select'
import { DEFAULT_VALUE_MAX_LEN } from '@/config'

export type InputsProps = {
    setInputs: (inputs: Record<string, any>) => boolean
    inputs: Record<string, any>
    promptConfig: PromptConfig
    inlineFlex?: boolean
    showLabel?: boolean
    className?: string
}

const Inputs: FC<InputsProps> = ({
    setInputs,
    inputs,
    promptConfig,
    inlineFlex = false,
    showLabel = true,
    className = ''
}) => {
    return (
        <div className={`space-y-3 p-4 ${inlineFlex && ' inline-flex'} ${className}`}>
            {promptConfig.prompt_variables.map(item => (
                <div className='tablet:flex items-start mobile:space-y-2 tablet:space-y-0 mobile:text-xs tablet:text-sm' key={item.key}>
                    {
                        showLabel && (
                            <label className={`flex-shrink-0 flex items-center tablet:leading-9 mobile:text-gray-700 tablet:text-gray-900 ${s.formLabel}`}>{item.name}</label>
                        )
                    }
                    {item.type === 'select'
                        && (
                            <Select
                                className='w-full'
                                defaultValue={inputs?.[item.key]}
                                onSelect={(i) => setInputs({ ...inputs, [item.key]: i.value })}
                                items={(item.options || []).map(i => ({ name: i, value: i }))}
                                allowSearch={true}
                                placeholder="選択してください"
                                bgClassName='bg-gray-50'
                            />
                        )}
                    {item.type === 'string' && (
                        <input
                            placeholder={`${item.name}${!item.required ? `(${t('app.variableTable.optional')})` : ''}`}
                            value={inputs?.[item.key] || ''}
                            onChange={(e) => { setInputs({ ...inputs, [item.key]: e.target.value }) }}
                            className={'w-full flex-grow py-2 pl-3 pr-3 box-border rounded-lg bg-gray-50'}
                            maxLength={item.max_length || DEFAULT_VALUE_MAX_LEN}
                        />
                    )}
                    {item.type === 'paragraph' && (
                        <textarea
                            className="w-full h-[104px] flex-grow py-2 pl-3 pr-3 box-border rounded-lg bg-gray-50"
                            placeholder={`${item.name}${!item.required ? `(${t('app.variableTable.optional')})` : ''}`}
                            value={inputs?.[item.key] || ''}
                            onChange={(e) => { setInputs({ ...inputs, [item.key]: e.target.value }) }}
                        />
                    )}
                </div>
            ))}
        </div>
    )
}

export default Inputs
