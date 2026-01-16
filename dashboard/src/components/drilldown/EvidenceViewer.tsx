import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { 
  Play, 
  Pause, 
  Volume2, 
  Download, 
  Mail, 
  User, 
  FileText,
  Clock,
  Speaker,
  X
} from 'lucide-react';

interface AudioEvidence {
  filename: string;
  allFilenames?: string[];
  fileCount?: number;
  duration: string;
  transcript: string;
  speakers: {
    client: string[];
    dealer: string[];
  };
  callStart: string;
  callEnd: string;
  mobileNumber: string;
}

interface EmailEvidence {
  subject: string;
  sender: string;
  recipient: string;
  date: string;
  content: string;
  attachments?: string[];
  clientCode: string;
  symbol: string;
  quantity: number;
  price: string;
  action: string;
}

interface EvidenceViewerProps {
  type: 'audio' | 'email';
  evidence: AudioEvidence | EmailEvidence;
  orderId: string;
  orderDetails?: {
    symbol: string;
    quantity: number;
    price: number;
    buySell: 'BUY' | 'SELL';
    clientId: string;
    clientName: string;
    orderDate: string;
  };
  onClose: () => void;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  type,
  evidence,
  orderId,
  orderDetails,
  onClose
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(50);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);

  const handlePlayPause = () => {
    if (!audioElement) return;
    
    if (isPlaying) {
      audioElement.pause();
    } else {
      audioElement.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleVolumeChange = (newVolume: number) => {
    setVolume(newVolume);
    if (audioElement) {
      audioElement.volume = newVolume / 100;
    }
  };

  const handleTimeUpdate = React.useCallback(() => {
    if (audioElement) {
      setCurrentTime(audioElement.currentTime);
    }
  }, [audioElement]);

  const handleLoadedMetadata = React.useCallback(() => {
    if (audioElement) {
      setDuration(audioElement.duration);
    }
  }, [audioElement]);

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (audioElement) {
      audioElement.currentTime = newTime;
    }
  };

  // Initialize audio element when component mounts
  React.useEffect(() => {
    if (type === 'audio') {
      const audioEvidence = evidence as AudioEvidence;
      const audio = new Audio();
      
      // Construct the audio file path with full backend URL
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const audioPath = `${apiUrl}/api/surveillance/audio-file/${audioEvidence.filename}`;
      audio.src = audioPath;
      audio.volume = volume / 100;
      
      audio.addEventListener('timeupdate', handleTimeUpdate);
      audio.addEventListener('loadedmetadata', handleLoadedMetadata);
      audio.addEventListener('ended', () => setIsPlaying(false));
      audio.addEventListener('error', (e) => {
        console.error('Audio loading error:', e);
        console.error('Audio src:', audio.src);
        console.error('Audio networkState:', audio.networkState);
        console.error('Audio readyState:', audio.readyState);
        console.error('Audio error details:', audio.error);
        
        // Check if it's a format issue
        if (audio.error && audio.error.code === 4) {
          setAudioError('Audio format not supported by browser (telephony format)');
        } else {
          setAudioError(`Audio loading failed: ${audio.error?.message || 'Unknown error'}`);
        }
      });
      audio.addEventListener('loadstart', () => {
        console.log('Audio loading started:', audio.src);
      });
      audio.addEventListener('canplay', () => {
        console.log('Audio can play:', audio.src);
      });
      
      setAudioElement(audio);
      
      return () => {
        audio.removeEventListener('timeupdate', handleTimeUpdate);
        audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
        audio.removeEventListener('ended', () => setIsPlaying(false));
        audio.pause();
      };
    }
  }, [type, evidence, volume, handleTimeUpdate, handleLoadedMetadata]);

  const handleDownload = () => {
    if (type === 'audio') {
      const audioEvidence = evidence as AudioEvidence;
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const audioPath = `${apiUrl}/api/surveillance/audio-file/${audioEvidence.filename}`;
      window.open(audioPath, '_blank');
    } else {
      console.log('Downloading evidence for order:', orderId);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (type === 'audio') {
    const audioEvidence = evidence as AudioEvidence;
    
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <Card className="w-full max-w-4xl max-h-[90vh] overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Speaker className="h-5 w-5" />
              Audio Evidence - Order {orderId}
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </CardHeader>
          
          <CardContent className="space-y-6 overflow-y-auto max-h-[calc(90vh-120px)]">
            {/* Audio Player */}
            <div className="bg-gray-50 p-4 rounded-lg">
              {audioError && (
                <div className="mb-4 p-3 bg-yellow-100 border border-yellow-300 rounded-lg">
                  <p className="text-yellow-700 text-sm font-medium">Audio Playback Not Available</p>
                  <p className="text-yellow-600 text-xs mt-1">
                    The audio file format (16-bit mono 8000 Hz) is not supported by your browser. 
                    This is common with telephony recordings. You can:
                  </p>
                  <ul className="text-yellow-600 text-xs mt-2 ml-4 list-disc">
                    <li>View the complete transcript below</li>
                    <li>Download the audio file to play in an external player</li>
                    <li>Use a media player that supports telephony formats (VLC, QuickTime)</li>
                    <li>Try refreshing the page or using a different browser</li>
                  </ul>
                  <div className="mt-3">
                    <Button 
                      onClick={handleDownload}
                      variant="outline" 
                      size="sm"
                      className="text-yellow-700 border-yellow-300 hover:bg-yellow-200"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Download Audio File
                    </Button>
                  </div>
                </div>
              )}
              <div className="flex items-center gap-4 mb-4">
                <Button
                  onClick={handlePlayPause}
                  size="sm"
                  className="h-10 w-10 rounded-full"
                  disabled={!!audioError}
                >
                  {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </Button>
                
                <div className="flex-1">
                  <div className="text-sm font-medium">
                    {audioEvidence.fileCount && audioEvidence.fileCount > 1 
                      ? `${audioEvidence.fileCount} Audio Files` 
                      : audioEvidence.filename}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Duration: {duration > 0 ? formatDuration(duration) : audioEvidence.duration}
                  </div>
                  {audioEvidence.allFilenames && audioEvidence.allFilenames.length > 1 && (
                    <div className="text-xs text-muted-foreground mt-1 max-w-md truncate">
                      Files: {audioEvidence.allFilenames.join(', ')}
                    </div>
                  )}
                </div>
                
                <div className="flex items-center gap-2">
                  <Volume2 className="h-4 w-4" />
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={volume}
                    onChange={(e) => handleVolumeChange(Number(e.target.value))}
                    className="w-20"
                  />
                </div>
                
                <Button variant="outline" size="sm" onClick={handleDownload}>
                  <Download className="h-4 w-4 mr-2" />
                  Download
                </Button>
              </div>
              
              {/* Progress Bar */}
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-primary h-2 rounded-full transition-all duration-300"
                  style={{ width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>{formatDuration(currentTime)}</span>
                <span>{duration > 0 ? formatDuration(duration) : audioEvidence.duration}</span>
              </div>
              
              {/* Seek Bar */}
              {duration > 0 && (
                <input
                  type="range"
                  min="0"
                  max={duration}
                  value={currentTime}
                  onChange={handleSeek}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
              )}
            </div>

            {/* Call Information */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Call Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Clock className="h-4 w-4" />
                    <span>Start: {audioEvidence.callStart}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Clock className="h-4 w-4" />
                    <span>End: {audioEvidence.callEnd}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <User className="h-4 w-4" />
                    <span>Mobile: {audioEvidence.mobileNumber}</span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Speaker Analysis</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="text-sm">
                    <span className="font-medium text-blue-600">Client:</span> {audioEvidence.speakers.client.length} segments
                  </div>
                  <div className="text-sm">
                    <span className="font-medium text-green-600">Dealer:</span> {audioEvidence.speakers.dealer.length} segments
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Order Details */}
            {orderDetails && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Order Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-xs text-muted-foreground">Symbol</div>
                      <div className="font-medium">{orderDetails.symbol}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Quantity</div>
                      <div className="font-medium">{orderDetails.quantity.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Price</div>
                      <div className="font-medium">₹{orderDetails.price.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Action</div>
                      <div className={`font-medium ${orderDetails.buySell === 'BUY' ? 'text-green-600' : 'text-red-600'}`}>
                        {orderDetails.buySell}
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                    <div>
                      <div className="text-xs text-muted-foreground">Client ID</div>
                      <div className="font-medium">{orderDetails.clientId}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Client Name</div>
                      <div className="font-medium">{orderDetails.clientName}</div>
                    </div>
                  </div>
                  <div className="mt-4">
                    <div className="text-xs text-muted-foreground">Order Date</div>
                    <div className="font-medium">{orderDetails.orderDate}</div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Transcript */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Call Transcript</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-50 p-4 rounded-lg max-h-60 overflow-y-auto">
                  <pre className="text-sm whitespace-pre-wrap font-mono">
                    {audioEvidence.transcript}
                  </pre>
                </div>
              </CardContent>
            </Card>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (type === 'email') {
    const emailEvidence = evidence as EmailEvidence;
    
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <Card className="w-full max-w-4xl max-h-[90vh] overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Email Evidence - Order {orderId}
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </CardHeader>
          
          <CardContent className="space-y-6 overflow-y-auto max-h-[calc(90vh-120px)]">
            {/* Email Header */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  <span className="font-medium">{emailEvidence.subject}</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">From:</span> {emailEvidence.sender}
                  </div>
                  <div>
                    <span className="text-muted-foreground">To:</span> {emailEvidence.recipient}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Date:</span> {emailEvidence.date}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Client:</span> {emailEvidence.clientCode}
                  </div>
                </div>
              </div>
            </div>

            {/* Trade Instructions */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Trade Instructions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <div className="text-xs text-muted-foreground">Symbol</div>
                    <div className="font-medium">{emailEvidence.symbol}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Quantity</div>
                    <div className="font-medium">{emailEvidence.quantity.toLocaleString()}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Price</div>
                    <div className="font-medium">{emailEvidence.price}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Action</div>
                    <div className={`font-medium ${emailEvidence.action === 'BUY' ? 'text-green-600' : 'text-red-600'}`}>
                      {emailEvidence.action}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Email Content */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Email Content</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-50 p-4 rounded-lg max-h-60 overflow-y-auto">
                  <pre className="text-sm whitespace-pre-wrap">
                    {emailEvidence.content}
                  </pre>
                </div>
              </CardContent>
            </Card>

            {/* Attachments */}
            {emailEvidence.attachments && emailEvidence.attachments.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Attachments</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {emailEvidence.attachments.map((attachment, index) => (
                      <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                        <div className="flex items-center gap-2">
                          <FileText className="h-4 w-4" />
                          <span className="text-sm">{attachment}</span>
                        </div>
                        <Button variant="outline" size="sm">
                          <Download className="h-3 w-3 mr-1" />
                          Download
                        </Button>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="flex justify-end">
              <Button onClick={handleDownload} variant="outline">
                <Download className="h-4 w-4 mr-2" />
                Download Email
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return null;
};
