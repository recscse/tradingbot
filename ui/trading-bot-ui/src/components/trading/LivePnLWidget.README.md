# Live P&L Widget

A compact, always-visible floating widget that displays real-time profit and loss for active trading positions.

## Features

- **Always Visible**: Floats at bottom-right corner of screen on all pages
- **Real-time Updates**: Automatically updates P&L as market prices change via WebSocket
- **Responsive Design**: Works seamlessly on mobile, tablet, and desktop
- **Tailwind CSS**: Modern styling with gradient backgrounds and smooth animations
- **Interactive Controls**:
  - Minimize/Maximize toggle
  - Hide/Show widget
  - Manual refresh button
  - Connection status indicator

## Usage

The widget is automatically included in all protected routes via the `ProtectedLayout` wrapper in `App.js`.

```jsx
// Already included - no manual import needed
<ProtectedLayout>
  <YourPage />
</ProtectedLayout>
```

## Data Flow

1. **Initial Load**: Fetches active positions from `/api/v1/trading/execution/active-positions`
2. **Real-time Updates**: Listens to market data via `useUnifiedMarketData` hook
3. **P&L Calculation**: Automatically recalculates when positions or prices change

## Component Structure

```
LivePnLWidget/
├── Header (with connection status, minimize, close buttons)
├── Total P&L Summary
├── Position List (scrollable)
│   └── Individual Position Cards
│       ├── Symbol & Trade Type (BUY/SELL)
│       ├── P&L Amount & Percentage
│       └── Entry Price, Current Price, Quantity
└── Footer (with refresh button and status)
```

## Styling

Uses Tailwind CSS classes with custom gradients:
- Background: `bg-gradient-to-br from-gray-900 to-gray-800`
- Header: `bg-gradient-to-r from-blue-600 to-blue-700`
- Profit: `text-green-400`
- Loss: `text-red-400`

## Responsive Breakpoints

- Mobile: `w-80` (320px)
- Desktop: `sm:w-96` (384px)
- Max width: `max-w-full` (prevents overflow)

## State Management

- `positions`: Array of active trading positions
- `totalPnL`: Calculated sum of all position P&L
- `isMinimized`: Toggle for minimizing the widget
- `isVisible`: Toggle for hiding/showing the widget

## API Integration

### Endpoint
`GET /api/v1/trading/execution/active-positions`

### Response Format
```json
[
  {
    "position_id": 1,
    "symbol": "RELIANCE",
    "signal_type": "BUY",
    "entry_price": 2500.00,
    "current_price": 2520.00,
    "quantity": 10,
    "instrument_key": "NSE_EQ|INE002A01018"
  }
]
```

## Icons Used

From `lucide-react`:
- `TrendingUp`: Profit indicator
- `TrendingDown`: Loss indicator
- `Minimize2`: Minimize button
- `Maximize2`: Maximize button
- `X`: Close button

## Customization

To modify the widget appearance, update the Tailwind classes in the component:

```jsx
// Change position
className="fixed bottom-4 right-4"  // Try: top-4, left-4, etc.

// Change size
className="w-80 sm:w-96"  // Try: w-64, w-full, etc.

// Change colors
from-blue-600 to-blue-700  // Try: from-purple-600 to-purple-700
```

## Performance

- Lightweight: Only re-renders when positions or market data changes
- Optimized: Uses React hooks for efficient state management
- Minimal API calls: Fetches data once, then relies on WebSocket for updates

## Browser Compatibility

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Mobile browsers: Full support with responsive design

## Future Enhancements

- Draggable positioning
- Position size presets (minimize to icon only)
- Sound alerts for profit/loss thresholds
- Export positions to CSV
- Position-level stop loss/target visualization
