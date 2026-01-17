export default defineEventHandler(async (event) => {
  const body = await readBody(event)

  if (!body.email || !body.password) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Email and password are required'
    })
  }

  await new Promise(resolve => setTimeout(resolve, 500))

  if (body.email === 'demo@example.com' && body.password === 'password') {
    setCookie(event, 'auth_token', 'mock-jwt-token', {
      httpOnly: true,
      maxAge: body.rememberMe ? 60 * 60 * 24 * 7 : 60 * 60 * 24
    })

    return {
      user: {
        id: 1,
        name: 'Demo User',
        email: 'demo@example.com',
        avatar: 'https://github.com/benjamincanac.png'
      },
      token: 'mock-jwt-token'
    }
  }

  throw createError({
    statusCode: 401,
    statusMessage: 'Invalid email or password'
  })
})
