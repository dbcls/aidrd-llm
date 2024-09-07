export const dynamic = 'force-dynamic'

import { type NextRequest } from 'next/server'
import { NextResponse } from 'next/server'
import { knowledgeClient, getInfo, setSession } from '@/app/api/utils/common'

export async function GET(request: NextRequest) {
    const { sessionId, user } = getInfo(request)
    const limit = request.nextUrl.searchParams.get('limit') || 100
    try {
        const { data }: any = await knowledgeClient.sendRequest(
            'get',
            '/datasets',
            {},
            {

                limit
            },
        )

        return NextResponse.json(data, {
            headers: setSession(sessionId),
        })
    } catch (error) {
        return NextResponse.json([]);
    }
}
