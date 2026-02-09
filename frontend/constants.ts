import { Monitor, LogEntry, MonitorType } from './types';

export const MOCK_MONITORS: Monitor[] = [
  {
    id: 'm1',
    name: 'Warehouse Shelf A',
    type: 'QUANTIFIER',
    source: 'RTSP Stream 01',
    status: 'OK',
    lastUpdate: 'Just now',
    rule: 'Count boxes on Shelf A. Alert if < 50.',
    integrations: ['Excel Sheet'],
    thumbnailUrl: 'https://picsum.photos/400/225?random=1'
  },
  {
    id: 'm2',
    name: 'Safety Gate 3',
    type: 'DETECTOR',
    source: 'Event Trigger',
    status: 'ALERT',
    lastUpdate: '2 min ago',
    rule: 'Ensure all personnel are wearing hard hats.',
    integrations: ['WhatsApp', 'Email'],
    thumbnailUrl: 'https://picsum.photos/400/225?random=2'
  },
  {
    id: 'm3',
    name: 'Assembly Line 4',
    type: 'PROCESS',
    source: 'RTSP Stream 02',
    status: 'OK',
    lastUpdate: '10 sec ago',
    rule: 'Track assembly progress of Unit X-99.',
    integrations: ['Email'],
    thumbnailUrl: 'https://picsum.photos/400/225?random=3'
  }
];

export const generateMockLogs = (): LogEntry[] => {
  return [
    {
      id: 'l1',
      monitorId: 'm1',
      monitorName: 'Warehouse Shelf A',
      monitorType: 'QUANTIFIER',
      timestamp: '10:42:05 AM',
      isAlert: false,
      data: {
        sections: [
          { name: 'Top Rack', count: 45, status: 'OK' },
          { name: 'Mid Rack', count: 32, status: 'OK' },
          { name: 'Bottom Rack', count: 12, status: 'OK' }
        ]
      }
    },
    {
      id: 'l2',
      monitorId: 'm2',
      monitorName: 'Safety Gate 3',
      monitorType: 'DETECTOR',
      timestamp: '10:41:55 AM',
      isAlert: true,
      data: {
        checks: [
          { rule: 'Person Detected', pass: true },
          { rule: 'Vest Visible', pass: true },
          { rule: 'Hard Hat Visible', pass: false }
        ]
      }
    },
    {
      id: 'l3',
      monitorId: 'm3',
      monitorName: 'Assembly Line 4',
      monitorType: 'PROCESS',
      timestamp: '10:41:30 AM',
      isAlert: false,
      data: {
        progress: 75,
        stage: 'Component Installation',
        details: 'Installing circuit board module'
      }
    },
    {
      id: 'l4',
      monitorId: 'm1',
      monitorName: 'Warehouse Shelf A',
      monitorType: 'QUANTIFIER',
      timestamp: '10:40:12 AM',
      isAlert: true,
      data: {
        sections: [
          { name: 'Top Rack', count: 4, status: 'LOW' },
          { name: 'Mid Rack', count: 30, status: 'OK' },
          { name: 'Bottom Rack', count: 10, status: 'OK' }
        ]
      }
    },
    {
      id: 'l5',
      monitorId: 'm3',
      monitorName: 'Assembly Line 4',
      monitorType: 'PROCESS',
      timestamp: '10:39:45 AM',
      isAlert: false,
      data: {
        progress: 40,
        stage: 'Chassis Prep',
        details: 'Cleaning surface for bonding'
      }
    }
  ];
};
