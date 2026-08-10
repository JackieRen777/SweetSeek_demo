import React from 'react';
import FeatureSection from '../../components/ui/FeatureSection';
import './SweetPredictionSection.css';

interface Props {
  onTryNow: () => void;
}

const SweetPredictionSection: React.FC<Props> = ({ onTryNow }) => (
  <FeatureSection
    reversed
    title={<span>Sweet <span className="text-blue-600">Prediction</span></span>}
    description="Estimate relative sweetness from molecular structure and sensory descriptors. SweetSeek turns chemical insight into a clear, evidence-backed prediction in seconds."
    onTryNow={onTryNow}
    buttonLabel="Try Now！"
    visualComponent={
      <div className="prediction-original-art" aria-hidden="true">
        <div className="prediction-original-orbit prediction-original-orbit-one" />
        <div className="prediction-original-orbit prediction-original-orbit-two" />
        <div className="prediction-original-panel">
          <div className="prediction-original-head">
            <span className="prediction-original-dot" />
            <span>Sweetness model</span>
            <span className="prediction-original-live">LIVE</span>
          </div>
          <div className="prediction-original-molecule">
            <span className="prediction-original-atom prediction-original-atom-a" />
            <span className="prediction-original-atom prediction-original-atom-b" />
            <span className="prediction-original-atom prediction-original-atom-c" />
            <span className="prediction-original-bond prediction-original-bond-a" />
            <span className="prediction-original-bond prediction-original-bond-b" />
            <span className="prediction-original-bond prediction-original-bond-c" />
          </div>
          <div className="prediction-original-input">
            <span className="prediction-original-input-label">Molecular input</span>
            <strong>Reb-A</strong>
            <span className="prediction-original-input-chip">SMILES</span>
          </div>
          <div className="prediction-original-chart">
            <div className="prediction-original-line" />
            <span className="prediction-original-point prediction-original-point-one" />
            <span className="prediction-original-point prediction-original-point-two" />
            <span className="prediction-original-point prediction-original-point-three" />
            <span className="prediction-original-point prediction-original-point-four" />
          </div>
          <div className="prediction-original-result">
            <span>Predicted relative sweetness</span>
            <strong>218×</strong>
            <em>confidence 0.94</em>
          </div>
        </div>
      </div>
    }
  />
);

export default SweetPredictionSection;
