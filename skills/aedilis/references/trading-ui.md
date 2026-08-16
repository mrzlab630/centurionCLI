# Trading & Finance UI Patterns — AEDILIS Reference

## Dashboard Information Hierarchy

Top to bottom priority:
1. **Hero number** — Portfolio total value + 24h change (biggest, boldest)
2. **Active positions** — Scrollable cards or list with P&L per position
3. **Quick-action bar** — Buy / Sell / Copy (always visible, sticky)
4. **Recent activity feed** — Last trades, deposits, withdrawals
5. **Market overview** — Watchlist, trending tokens

## Real-Time Data Display

| Pattern | When to Use |
|---|---|
| **Batched updates** | >5 updates/sec → buffer 200ms, render once |
| **Virtualized lists** | >100 rows → render only visible |
| **Delta updates** | WebSocket sends changed fields only |
| **Snapshot + subscribe** | Initial REST fetch → WebSocket incremental |
| **Stale indicator** | Show "Last updated: Xs ago" if connection lost |

## Color Semantics

### Light Mode
| Meaning | Color | Hex |
|---|---|---|
| Profit / Up | Green | `#22C55E` |
| Loss / Down | Red | `#EF4444` |
| Neutral | Gray | `#6B7280` |
| Warning | Amber | `#F59E0B` |
| Info | Blue | `#3B82F6` |

### Dark Mode (desaturated for OLED)
| Meaning | Color | Hex |
|---|---|---|
| Profit / Up | Emerald | `#34D399` |
| Loss / Down | Red lighter | `#F87171` |
| Neutral | Gray | `#9CA3AF` |
| Warning | Amber lighter | `#FBBF24` |
| Info | Blue lighter | `#60A5FA` |

### Rules
- Never use color ALONE — always pair with ▲/▼ arrows, +/- signs, or icons
- Configurable color mapping for CJK markets (Red=profit, Green=loss in JP/CN/KR)
- Use semi-transparent backgrounds for P&L indicators: `rgba(color, 0.12)`

## Number Formatting

| Type | Format | Example |
|---|---|---|
| Fiat USD | `$1,234.56` | Two decimals, comma separator |
| SOL amount | `1.2345 SOL` | Four decimals for display |
| Token amount | Smart precision | `0.00001234` or `1.23M` |
| Percentage | `+12.5%` or `-3.2%` | Always show sign, one decimal |
| Large numbers | Abbreviated | `$1.2M`, `$456K`, `$1.2B` |
| Addresses | Truncated | `7A77...K8Dz` (4+4) with copy button |
| TX hash | Truncated | `abc1...ef23` with explorer link |
| Time | Relative | "2m ago", "1h ago", "3d ago" |

## Position Card Design

```
┌─────────────────────────────┐
│ 🪙 TOKEN/SOL    +12.5% ▲   │  ← Token pair + P&L color-coded
│ Entry: 0.0034  Now: 0.0038  │  ← Prices
│ Size: 1.5 SOL  P&L: +0.19  │  ← Position size + absolute P&L
│ ⏱ 2h 15m        [Sell 50%] │  ← Hold time + action button
└─────────────────────────────┘
```

## Trade Confirmation Flow

```
Step 1: User taps "Buy" → Show confirmation sheet
Step 2: Display: Token, Amount, Estimated Price, Slippage, Fees
Step 3: Two buttons: [Cancel] [Confirm Buy]
Step 4: On confirm → Loading state with spinner
Step 5a: Success → Green flash + details + "View Position"
Step 5b: Failure → Red flash + specific error + "Retry"
```

## Transaction Status Indicators

```
⏳ Pending     → Spinner animation
🔄 Confirming  → Progress indicator (1/32 confirmations)
✅ Confirmed   → Green checkmark + TX link
❌ Failed      → Red X + error reason + retry option
⚠️ Partial     → Warning + details of what succeeded/failed
```

## Trading-Specific Patterns

### Slippage Display
- Always visible during trade confirmation
- Color-code: green (<1%), yellow (1-3%), red (>3%)
- Show estimated vs actual after trade completes

### Order Book / Price Display
- Green for bids (buy side), Red for asks (sell side)
- Depth visualization as horizontal bars
- Mid-price highlighted and largest

### Portfolio Allocation
- Donut/pie chart for distribution
- Sorted by value (largest first)
- "Other" category for <2% positions
- Show allocation % next to each token

### Trust & Security Patterns
1. Lock icon + "Encrypted" labels near sensitive operations
2. Two-step confirmation for trades >$100 equivalent
3. Error transparency: specific message, never "Something went wrong"
4. Show signing details before transaction approval
5. Activity log accessible for audit trail

## Mobile Trading Patterns

- **Bottom sheet** for trade execution (swipe up to expand)
- **Pull-to-refresh** for portfolio updates
- **Haptic feedback** on trade confirmations (Vibration API)
- **Swipe gestures** for quick-sell (swipe left = sell)
- **Sticky headers** for token price while scrolling position details
- **FAB (Floating Action Button)** for primary action (Buy/Trade)
