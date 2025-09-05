import React from 'react';

/**
 * A tooltip component that displays a message when the user hovers over an element.
 *
 * @param {object} props - The component props.
 * @param {string} props.text - The text to display in the tooltip.
 * @param {React.ReactNode} props.children - The element to which the tooltip is attached.
 * @returns {JSX.Element} The rendered component.
 */
const Tooltip = ({ text, children }: { text: string; children: React.ReactNode }) => (
    <div className="tooltip">
        {children}
        <span className="tooltiptext">{text}</span>
    </div>
);

export default Tooltip;
