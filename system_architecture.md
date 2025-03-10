flowchart TB
    subgraph External Data Sources
        MD[Market Data Feeds]
        NF[News Feeds]
        EI[Economic Indicators]
    end

    subgraph Data Integration Layer
        DIP[Data Integration Pipeline]
        DST[Data Storage]
        DPP[Data Preprocessing]
    end

    subgraph Agent Network
        TA[Technical Analysis Agent]
        FA[Fundamental Analysis Agent]
        RM[Risk Management Agent]
        SO[Strategy Optimization Agent]
        TE[Trade Execution Agent]
        
        MB[Message Broker]
        
        TA <-->|Analysis & Signals| MB
        FA <-->|Economic Impact Assessment| MB
        RM <-->|Risk Parameters| MB
        SO <-->|Optimized Strategies| MB
        TE <-->|Execution Status| MB
    end

    subgraph Execution & Monitoring
        TG[Trading Gateway]
        PM[Performance Monitor]
        AL[Audit Logger]
    end

    External Data Sources -->|Raw Data| Data Integration Layer
    Data Integration Layer -->|Processed Data| Agent Network
    Agent Network -->|Trade Decisions| Execution & Monitoring
    Execution & Monitoring -->|Feedback| Agent Network
