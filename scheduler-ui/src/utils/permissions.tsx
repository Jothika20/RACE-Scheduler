export const hasPermission = (
    permissions: Record<string, boolean> | undefined,
    key: string
): boolean => {
    if (!permissions) return false;
    return !!permissions[key];
};
