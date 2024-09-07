export const dynamic = 'force-dynamic'

import { type NextRequest } from 'next/server'
import { NextResponse } from 'next/server'
import { knowledgeClient, getInfo, setSession } from '@/app/api/utils/common'

export async function GET(request: NextRequest, params: { params: { datasetId: string } }) {
    const { sessionId, user } = getInfo(request)
    const originalLimit = request.nextUrl.searchParams.get('limit')
    const limit = Math.min(request.nextUrl.searchParams.get('limit'), 100) // 100 is the max limit for Dify API
    const { datasetId } = params.params
    let wholeData: any[] = []

    try {
        let page = 1
        let apiResult: any
        do {
            apiResult = (await knowledgeClient.sendRequest(
                'get',
                `/datasets/${datasetId}/documents`,
                {},
                {
                    limit,
                    page: page++
                },
            )).data
            wholeData = wholeData.concat(apiResult.data as any[])
        } while (apiResult.has_more && wholeData.length < originalLimit)

        return NextResponse.json(wholeData, {
            headers: setSession(sessionId),
        })
    } catch (error) {
        console.log(error)
        return NextResponse.json([]);
    }
}
