export interface User {
  id: number
  name: string
  email: string
  avatar?: string | null
}

export interface AuthResponse {
  user: User
  token: string
}
