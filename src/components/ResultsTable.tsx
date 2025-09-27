import React from 'react';

const tableStyles: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  marginTop: '20px',
  color: '#fff',
};

const thStyles: React.CSSProperties = {
  border: '1px solid #555',
  padding: '10px',
  backgroundColor: '#3a3a3a',
  textAlign: 'left',
};

const tdStyles: React.CSSProperties = {
  border: '1px solid #555',
  padding: '8px',
  textAlign: 'left',
};

interface ResultsTableProps {
  alerts: any[];
}

const ResultsTable: React.FC<ResultsTableProps> = ({ alerts }) => {
  if (alerts.length === 0) {
    return <p>Nenhum alerta foi gerado para os critérios selecionados.</p>;
  }

  return (
    <table style={tableStyles}>
      <thead>
        <tr>
          <th style={thStyles}>Data e Hora</th>
          <th style={thStyles}>Condição do Alerta</th>
          <th style={thStyles}>Descrição</th>
          <th style={thStyles}>Preço (USD)</th>
        </tr>
      </thead>
      <tbody>
        {alerts.map((alert, index) => (
          <tr key={index}>
            <td style={tdStyles}>{new Date(alert.timestamp).toLocaleString('pt-BR')}</td>
            <td style={tdStyles}>{alert.condition}</td>
            <td style={tdStyles}>{alert.description}</td>
            <td style={tdStyles}>${alert.price.toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default ResultsTable;