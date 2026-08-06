/**
 * ML Prediction Section Wrapper
 * Simplified to match other features (no fixed overlay)
 */

import MLPredictInterface from './components/MLPredictInterface';

interface Props {
  onClose?: () => void;
}

export default function MLPredictSection(_props: Props) {
  return <MLPredictInterface />;
}
