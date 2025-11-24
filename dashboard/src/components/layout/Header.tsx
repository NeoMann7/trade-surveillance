import React from 'react';
import { Button } from '../ui/button';
import { Shield, Settings, User, Bell } from 'lucide-react';

interface HeaderProps {
  onSettings: () => void;
  onNotifications: () => void;
  onUserProfile: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onSettings,
  onNotifications,
  onUserProfile
}) => {
  return (
    <header className="h-16 bg-card border-b border-border flex items-center justify-between px-6">
      {/* Left side - Logo and Title */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Shield className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-xl font-bold text-foreground">Trade Surveillance Dashboard</h1>
            <p className="text-sm text-muted-foreground">Comprehensive monitoring and analysis</p>
          </div>
        </div>
      </div>

      {/* Right side - Actions */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onNotifications}
          className="relative"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full text-xs text-white flex items-center justify-center">
            3
          </span>
        </Button>
        
        <Button
          variant="ghost"
          size="icon"
          onClick={onSettings}
        >
          <Settings className="h-5 w-5" />
        </Button>
        
        <Button
          variant="ghost"
          size="icon"
          onClick={onUserProfile}
        >
          <User className="h-5 w-5" />
        </Button>
      </div>
    </header>
  );
};
