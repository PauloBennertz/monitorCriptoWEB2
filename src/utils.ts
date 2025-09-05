/**
 * Formats a number as a currency string.
 *
 * @param {number} value - The number to format.
 * @returns {string} The formatted currency string.
 */
export const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'USD' }).format(value);
};

/**
 * Formats a large number using compact notation.
 *
 * @param {number} value - The number to format.
 * @returns {string} The formatted number string.
 */
export const formatLargeNumber = (value: number) => {
    return new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 2 }).format(value);
};

/**
 * Formats a number of seconds into a time string (mm:ss).
 *
 * @param {number} seconds - The number of seconds to format.
 * @returns {string} The formatted time string.
 */
export const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
};
