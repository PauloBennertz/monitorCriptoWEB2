import React from 'react';
import { Alert } from '../types';
import { format } from 'date-fns';

interface ResultsTableProps {
  alerts: Alert[]; // O nome da prop deve ser 'alerts'
}

const ResultsTable: React.FC<ResultsTableProps> = ({ alerts }) => {
  if (!alerts || alerts.length === 0) {
    return <p>Nenhum alerta encontrado para os critérios selecionados.</p>;
  }

  return (
    <div className="results-table-container">
      <h4>Resultados da Análise</h4>
      <table className="results-table">
        <thead>
          <tr>
            <th>Data e Hora</th>
            <th>Condição do Alerta</th>
            <th>Preço no Momento</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert, index) => (
            <tr key={alert.id || index}>
              <td>{format(new Date(alert.timestamp), 'dd/MM/yyyy HH:mm:ss')}</td>
              <td>{alert.condition}</td>
              {/* CORREÇÃO AQUI: 
                Verificamos se 'alert.snapshot' e 'alert.snapshot.price' existem.
                Se não existirem, mostramos 'N/A' em vez de causar um erro.
              */}
              <td>
                {alert.snapshot && typeof alert.snapshot.price === 'number'
                  ? `$ ${alert.snapshot.price.toFixed(4)}`
                  : 'N/A'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ResultsTable;