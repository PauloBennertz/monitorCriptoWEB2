import React from 'react';

const Tooltip = ({ text, children }: { text: string; children: React.ReactNode }) => (
    <div className="tooltip">
        {children}
        <span className="tooltiptext">{text}</span>
    </div>
);

export default Tooltip;
