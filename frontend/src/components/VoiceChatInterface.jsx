import React, { useState, useEffect, useCallback, useRef } from 'react';
import { VoiceProvider, useVoice, ReadyState } from '@humeai/voice-react';
import { fetchHumeToken } from '../api'; // Assuming api.js is in src/

const ChatControls = () => {
  const { connect, disconnect, messages: humeMessages, readyState, sendCustomMessage, sendAudio } = useVoice();
  const [chatMessages, setChatMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // This effect processes messages received from the backend via the WebSocket,
    // which are assumed to be available in humeMessages or via a custom message handling mechanism.
    // The structure of humeMessages needs to be compatible with what our backend sends.
    // Our backend sends JSON strings like:
    // {"type": "transcription", "text": "..."}
    // {"type": "rag_response", "text": "..."}
    // {"type": "error", "source": "...", "message": "..."}
    // {"type": "system", "sub_type": "...", "message": "..."}

    if (humeMessages && humeMessages.length > 0) {
      const latestHumeMessage = humeMessages[humeMessages.length - 1];

      // We need to determine how custom messages from our backend are structured within latestHumeMessage.
      // Option 1: `latestHumeMessage.type === 'custom_message'` and `latestHumeMessage.message` is our JSON string or parsed object.
      // Option 2: `latestHumeMessage.type === 'user_message'` or `assistant_message` and it contains our payload.
      // For this implementation, we'll assume that `latestHumeMessage.type === 'custom_message'`
      // and `latestHumeMessage.message` contains the JSON payload sent by the backend.
      // This is a common pattern for SDKs that allow passthrough of custom data.

      let processedMessage = null;

      if (latestHumeMessage.type === 'custom_message' && latestHumeMessage.message) {
        const customData = latestHumeMessage.message; // Assuming this is already a parsed object
                                                     // If it's a string: const customData = JSON.parse(latestHumeMessage.message.content);

        if (customData.type === 'transcription') {
          processedMessage = { sender: 'User', text: customData.text, id: latestHumeMessage.id || Date.now() };
        } else if (customData.type === 'rag_response') {
          processedMessage = { sender: 'Assistant', text: customData.text, id: latestHumeMessage.id || Date.now() };
        } else if (customData.type === 'error') {
          processedMessage = { sender: 'System', text: `Error (${customData.source}): ${customData.message}`, id: latestHumeMessage.id || Date.now(), isError: true };
        } else if (customData.type === 'system') {
           processedMessage = { sender: 'System', text: `${customData.sub_type ? customData.sub_type + ': ' : ''}${customData.message}`, id: latestHumeMessage.id || Date.now() };
        }
      } else if (latestHumeMessage.type === 'user_message') {
        // This would be if Hume SDK itself transcribes and gives a user message
        // For our setup, backend sends transcription, so this might not be used directly for chat display unless backend is bypassed.
        // processedMessage = { sender: 'User', text: latestHumeMessage.message.content, id: latestHumeMessage.id };
      } else if (latestHumeMessage.type === 'assistant_message') {
        // This would be if Hume SDK itself generates assistant text response
        // For our setup, backend sends RAG response, so this might not be used directly.
        // processedMessage = { sender: 'Assistant', text: latestHumeMessage.message.content, id: latestHumeMessage.id };
      } else if (latestHumeMessage.type === 'error_message') {
        // Error from Hume SDK itself
        processedMessage = { sender: 'System', text: `Voice SDK Error: ${latestHumeMessage.message.content}`, id: latestHumeMessage.id, isError: true };
      }


      if (processedMessage) {
        setChatMessages(prevMessages => {
          // Avoid duplicating the last message if IDs are available and match
          if (prevMessages.length > 0 && processedMessage.id && prevMessages[prevMessages.length - 1].id === processedMessage.id) {
            return prevMessages;
          }
          return [...prevMessages, processedMessage];
        });
      }
    }
  }, [humeMessages]);

  const handleConnect = useCallback(() => {
    if (readyState === ReadyState.OPEN) return;
    setIsLoading(true);
    connect()
      .then(() => setIsLoading(false))
      .catch(e => {
        console.error("Connection error", e);
        setChatMessages(prev => [...prev, {sender: 'System', text: `Connection failed: ${e.message}`, isError: true, id: Date.now()}]);
        setIsLoading(false);
      });
  }, [connect, readyState]);

  const handleDisconnect = useCallback(() => {
    setIsLoading(true);
    disconnect()
      .then(() => setIsLoading(false))
      .catch(e => {
        console.error("Disconnection error", e);
        setIsLoading(false);
      });
  }, [disconnect]);

  const isConnected = readyState === ReadyState.OPEN;
  const isConnecting = readyState === ReadyState.CONNECTING || isLoading;

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button onClick={handleConnect} disabled={isConnected || isConnecting}>
          {isConnecting ? 'Connecting...' : (isConnected ? 'Connected' : 'Start Voice Chat')}
        </button>
        <button onClick={handleDisconnect} disabled={!isConnected || isConnecting}>
          {isConnecting && !isConnected ? 'Cancelling...' : 'Stop Voice Chat'}
        </button>
      </div>
      <div style={{ marginBottom: '10px', fontStyle: 'italic' }}>
        Connection Status: {ReadyState[readyState]}
      </div>
      <div style={{ border: '1px solid #ccc', height: '300px', overflowY: 'auto', padding: '10px', marginBottom: '10px' }}>
        {chatMessages.map((msg, index) => (
          <div key={msg.id || index} style={{ marginBottom: '5px', color: msg.isError ? 'red' : 'inherit' }}>
            <strong>{msg.sender}:</strong> {msg.text}
          </div>
        ))}
      </div>
      {/* Example of how to send audio if needed, though @humeai/voice-react typically handles mic internally */}
      {/* <button onClick={() => sendAudio(new ArrayBuffer(0))}>Send Blank Audio (Test)</button> */}
      {/* Example of how to send custom message if needed */}
      {/* <button onClick={() => sendCustomMessage(JSON.stringify({ type: "client_event", content: "button_click" }))}>Send Custom Event</button> */}
    </div>
  );
};

const VoiceChatInterface = () => {
  const [accessToken, setAccessToken] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchHumeToken()
      .then(tokenResponse => {
        if (tokenResponse && tokenResponse.access_token) {
          setAccessToken(tokenResponse.access_token);
        } else {
          throw new Error("Access token not found in response");
        }
      })
      .catch(err => {
        console.error("Failed to fetch Hume token:", err);
        setError(`Failed to load Hume token: ${err.message}. Voice chat will not be available.`);
      });
  }, []);

  if (error) {
    return <div style={{ color: 'red', padding: '20px' }}>{error}</div>;
  }

  if (!accessToken) {
    return <div style={{ padding: '20px' }}>Loading Hume AI session...</div>;
  }

  // Construct WebSocket URL from current window location
  // Ensure to use wss:// if the main page is loaded over https://
  const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
  const wsUrl = `${wsProtocol}${window.location.hostname}:8000/ws/voice-chat`;
  // For development, if frontend and backend are on different ports and backend is not on 8000:
  // const wsUrl = `${wsProtocol}localhost:8000/ws/voice-chat`; // Or your specific backend port

  return (
    <VoiceProvider
      auth={{ type: 'accessToken', value: accessToken }}
      configId={null} // Replace with your actual EVI configId if you have one
      url={wsUrl}
      onOpen={() => {
        console.log('VoiceProvider: Connection opened');
        // Can use this to update local state if needed, e.g. add a system message to chat
      }}
      onClose={(event) => {
        console.log('VoiceProvider: Connection closed', event);
      }}
      onError={(errorData) => {
        console.error('VoiceProvider: Error', errorData);
        // This error is from the VoiceProvider itself (e.g. auth failure, WebSocket connection error before Hume SDK takes over)
        // Child components using useVoice() will get more specific errors via ReadyState or messages.
        // We could set a global error state here too.
      }}
      // The `onMessage` prop might be useful if `useVoice().messages` isn't sufficient
      // for handling custom JSON messages from the backend.
      // onMessage={(event) => console.log('Raw WS Message from VoiceProvider:', event.data)}
    >
      <ChatControls />
    </VoiceProvider>
  );
};

export default VoiceChatInterface;
