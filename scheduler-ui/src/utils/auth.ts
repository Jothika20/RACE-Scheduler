export const logoutUser = () => {
    localStorage.removeItem('token');
    window.dispatchEvent(new Event('storage')); // trigger App state update
};
