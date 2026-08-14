import React from 'react';
import EncapsulationChatInterface from '../../encapsulation/components/EncapsulationChatInterface';
import { proteoglycanQAConfig } from '../proteoglycanQAConfig';

const ProteoglycanChatInterface: React.FC = () => (
  <EncapsulationChatInterface config={proteoglycanQAConfig} />
);

export default ProteoglycanChatInterface;
