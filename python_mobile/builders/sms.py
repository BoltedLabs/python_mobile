from typing import Tuple, List

from dataclasses import dataclass

import phonenumbers

@dataclass
class Message:
    phone: phonenumbers.phonenumber.PhoneNumber
    text: str

    def at_command(self) -> str:
        formatted_number = phonenumbers.format_number(self.phone, phonenumbers.PhoneNumberFormat.E164) 
        return f'AT+CMGS={formatted_number}\z{self.text}\z'

class SMSBuilder:
    def __init__(self, to: str, message: str, part: bool = True):
        self.to: phonenumbers.phonenumber.PhoneNumber = phonenumbers.parse(to, None)
        self._message: str = message
        self._messages: List[str] = []
        self._index: int = 0

        if part:
            split: List[str] = self._message.split(' ')
            chunks: List[Tuple[int, int]] = self._chunk(self._message, 160)

            messages: List[str] = []

            for index, chunk_ in enumerate(chunks): 
                counter: str = f'({len(chunks)}/{len(chunks)}) '

                string: Tuple[int, int] = split[chunk_[0]:chunk_[1]]
                string_count: int = len(' '.join(string))

                if len(counter) + int(string_count) > 160:
                    _counter: int = 1
                    
                    while True:
                        this_chunk: List[str] = split[ chunk_[0] : chunk_[1] - _counter ]
                        this_chunk_count: int = len(' '.join(this_chunk))

                        if this_chunk_count + len(counter) > 160:
                            _counter += 1
                        else:
                            chunks[ index ] = (chunk_[0], chunk_[1] - _counter)
                            try:
                                chunks[ index + 1 ] = (chunks [ index + 1 ][ 0 ] - _counter, chunks [ index + 1 ][1])
                            except IndexError:
                                chunks.append((chunks[ index ][1], len(split)))
                            break

            for index, chunk_ in enumerate(chunks):
                string: str = f'({index+1}/{len(chunks)}) ' + ' '.join(split[ chunk_[ 0 ] : chunk_[ 1 ] ])
                self._messages.append(Message(phone=self.to, text=string))

    def _chunk(self, l: str, n: int) -> List[Tuple[int, int]]:
        split: List[str] = l.split(' ')
        correct: bool = False

        messages: List[Tuple[int, int]]  = []
        position: int = 0

        starting: int = 0
        total_count: int = 0
        
        for index, item in enumerate(split):
            count: int = len(item)
            total_count += count + 1
            
            if total_count >= n:
                messages.append((starting, index))
                starting = index
                total_count = 0

        return messages

    
    def __iter__(self):
        return self

    def __next__(self):
        try:
            result = self._messages[self._index]
        except IndexError:
            raise StopIteration

        self._index += 1
        return result
