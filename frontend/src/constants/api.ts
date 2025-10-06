export const API_BASE_URL = {
    auth: '',  // Use relative URLs with Vite proxy
    leaderboard: ''  // Use relative URLs with Vite proxy
};

export const API_ENDPOINTS = {
    auth: {
        login: '/login',
        register: '/register',
        me: '/profile'
    },
    leaderboard: {
        get: '/leaderboard'
    }
};
