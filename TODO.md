TODO List for implementating FE-C trainer

X Change powermeter to pair as FEC

- Implement common page 80 (p 22, Sec 6.5 of "Common Data Pages" document)
  - mfg ID: 0x00ff is reserved for "dev"
  - model #: 15
  - hw rev #: 1.0
  - should send the following:
    0x50 (80), [0xff, 0xff], [0x01], [0xff, 0x00], [0x00, 0x01]

- Implement common page 81
  - sw rev #: 0.1
  - 32 bit s/n: 0xface
  - should send the following:
    0x51 (81), [0xff], [0xff], [0x01], [0xce, 0xfa, 0xed, 0xfe]
    
