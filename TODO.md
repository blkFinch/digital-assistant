TODO add desires?

TODO add soft context by adding (maybe) to memories with low confidence
TODO add custom errors to all the modules
TODO improve memory prompt - she is currently stuck on my name stuff and constantly revising. she wants a way to remove the memory. 
TODO she is too snarky. needs to be more dumb??

TODO upgrade to eleven labs TTS as API use Jessica Voice
TODO call for tts before reflection prompt
TODO create Reflection Worker with queue 

TODO how to handle memory clean up. she seems to have no way to remove some memories and its causing them to pile up, we need to keep them clean
    
    ## Memory System
    STM = Session Log (last 15 messages)
    LTM = Mem object has id, last_activated, keywords, embeddings, along with current fields
    WORKING Memory = LTM mem objects that are appended to prompts - should be 20 memories most recently activated *use it or lose it* 

    ### Memory Algo
    - embedding search for relavant LTM MAX=5 (potentially optimize by doing keyword search first)
    - append (MEM_MAX - returned_ltm.count) LTM sorted by most recently activated

    ### Memory Block Improvements
    - have `confidence` rating - Lowest confidence are filtered, medium confidence prepend "MAYBE" for fuzzy memory
    - include mem id's in initial prompt and have LLM return ids for memories it used in response

    ### Additional Improvements
    - simple Desire system - allow assistant to have 1-3 active Desires
    - can be LTM with desire type 