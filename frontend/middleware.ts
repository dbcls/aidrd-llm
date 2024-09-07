import { NextRequest, NextResponse } from 'next/server';

export const config = {
    matcher: ['/:path*']
}

export function middleware(req: NextRequest) {
    if (process.env.BASIC_AUTH_ENABLED.toLowerCase() !== 'true') {
        return NextResponse.next();
    }

    const basicAuth = req.headers.get('authorization');
    if (!basicAuth) {
        return new Response('Authentication required', {
            status: 401,
            headers: {
                'WWW-Authenticate': 'Basic realm="Secure Area"',
            },
        });
    }

    try {
        const authValue = basicAuth.split(' ')[1];
        const [user, pwd] = atob(authValue).split(':');

        if (user === process.env.BASIC_AUTH_ID && pwd === process.env.BASIC_AUTH_PASSWORD) {
            return NextResponse.next();
        }
    } catch (e) {
        console.log(e)
        return new Response('Invalid Authentication', { status: 400 });
    }

    return new Response('Unauthorized', { status: 401 });
}