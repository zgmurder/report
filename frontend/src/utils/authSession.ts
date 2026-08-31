export const ACCESS_TOKEN_KEY = 'report_access_token'
export const CURRENT_USER_KEY = 'report_current_user'

let redirectingToLogin = false

export function clearStoredAuth() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(CURRENT_USER_KEY)
}

export function currentRouteForRedirect() {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`
}

export function redirectToLogin(redirect = currentRouteForRedirect()) {
  clearStoredAuth()
  if (window.location.pathname === '/login' || redirectingToLogin) return

  redirectingToLogin = true
  const loginUrl = new URL('/login', window.location.origin)
  if (redirect && redirect !== '/login' && !redirect.startsWith('/login?')) {
    loginUrl.searchParams.set('redirect', redirect)
  }
  window.location.replace(`${loginUrl.pathname}${loginUrl.search}`)
}

export function handleUnauthorizedResponse(response: Pick<Response, 'status'>) {
  if (response.status !== 401) return false
  redirectToLogin()
  return true
}
