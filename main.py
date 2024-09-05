import numpy as np
import random
import pickle

import utils
from consts import *

class GameEnv:
    def __init__(self, num_players=4, num_decks=1, win_mode="individual", moveset=MOVESET_1, has_user=False, seed=None):
        self.num_players = num_players
        self.num_decks = num_decks
        self.win_mode = win_mode
        self.moveset = moveset
        self.has_user = has_user
        self.history = []
        
        self.reset(seed)

    def reset(self, seed=None):
        print(f"New game with {self.num_players} players and {self.num_decks} deck(s) of cards.")
        
        card_freq = np.array(CARD_FREQ) * self.num_decks
        cards_per_player = CARDS_PER_PLAYER[f"{self.num_players}_{self.num_decks}"]
        
        if seed is not None:
            print(f"Seed: {seed}")
            random.seed(seed)
        
        # Randomly divide into 4 piles of cards then decide which player gets which pile and who starts
        # Game mode must be individual or pairs (no landlord; assume individual for now)
        if self.num_players == 4:
            # Players start with empty hands
            self.hands = [np.array([0] * NUM_RANKS) for _ in range(self.num_players)]
            
            # Deal cards for each player
            for p in range(self.num_players-1):
                for card in range(cards_per_player[p]):
                    dealt = False
                    while not dealt:
                        idx = random.randint(0, NUM_RANKS-1)
                        if card_freq[idx] > 0:
                            card_freq[idx] -= 1
                            self.hands[p][idx] += 1
                            dealt = True
                            
            self.hands[-1] = card_freq
            
        # Decide the order that cards were dealt
        self.order = random.randint(0, self.num_players-1)
        self.hands = self.hands[self.order:] + self.hands[:self.order]
        
        if self.has_user:
            self.players = [NaivePlayer(hand=self.hands[p], moveset=self.moveset) for p in range(self.num_players - 1)]
            self.players.append(UserPlayer(hand=self.hands[-1], moveset=self.moveset))  # User player is always the last player
        else:
            self.players = [NaivePlayer(hand=self.hands[p], moveset=self.moveset) for p in range(self.num_players)]
        
    def play_game(self):
        for player in self.players:
            print(player.hand)
        print()
        
        # Start with a random player
        curr_player = random.randint(0, self.num_players-1)
        print(f"Player {curr_player} starts")
        
        self.players[curr_player].free = True
        pattern = None
        prev_choice = None
        leading_rank = None
        skip_count = 0
        
        # Players play in order until the game is over (empty hand)
        while True:
            # Record the current state
            curr_state = self.get_state(curr_player)
            
            # If all other players skip their turn, the current player is free to move
            if skip_count == self.num_players - 1:
                self.players[curr_player].free = True
                skip_count = 0
            
            contains_pattern, pattern, prev_choice, leading_rank, remainder = self.players[curr_player].move(pattern=pattern, prev_choice=prev_choice, leading_rank=leading_rank)
            
            if not contains_pattern:
                skip_count += 1
            else:
                skip_count = 0
            
            print(f"Player {curr_player} plays:")
            if contains_pattern:
                print(f"Choice: {prev_choice}, pattern: {pattern}, rank: {leading_rank}, card: {CARDS[leading_rank]}")
                print(self.players[curr_player].hand, remainder)
                print()
                for player in self.players:
                    print(player.hand)
            else:
                print(f"Skip. Skip count: {skip_count}")
            print()
            
            # Record the player action and new state
            action = {"player": curr_player,
                      "contains_pattern": contains_pattern,
                      "pattern": pattern,
                      "choice": prev_choice,
                      "leading_rank": leading_rank}
            new_state = self.get_state(curr_player)
            reward = self.calculate_reward(curr_player, contains_pattern, remainder)
            self.history.append({"state": curr_state, 
                                 "action": action, 
                                 "new_state": new_state, 
                                 "reward": reward})
            
            # Check if the game is over
            if remainder <= 0:
                break
            
            # Move on to the next player
            curr_player = (curr_player + 1) % self.num_players
            
        print(f"Game over. Winner is player {curr_player}")
        return self.history
        
    def get_state(self, curr_player):
        return {"curr_player": curr_player,
                "hands": [player.hand.copy() for player in self.players],
                "free": self.players[curr_player].free}

    def calculate_reward(self, curr_player, contains_pattern, remainder):
        if remainder == 0:
            return 10   # Win
        elif contains_pattern:
            return 0.1  # Successful move
        else:
            return -0.1 # Skipped turn
        
    def replay(self, history):
        for step in history:
            print(f"Player {step['action']['player']} action:")
            print(f"State: {step['state']}")
            print(f"Action: {step['action']}")
            print(f"New State: {step['new_state']}")
            print(f"Reward: {step['reward']}")
            print()

class NaivePlayer:
    def __init__(self, hand, moveset, free=False):
        self.hand = hand
        self.moveset = moveset
        self.free = free
        
    def move(self, pattern=None, prev_choice=None, leading_rank=-1):
        # If free to move, play the smallest available hand
        # Doesn't care about previous cards or leading rank
        if self.free:
            leading_rank = -1   # Reset the leading rank
            self.free = False
            random.shuffle(self.moveset)
            for pattern in self.moveset:
                contains_pattern, pattern, choice, leading_rank = utils.smallest_valid_choice(hand=self.hand, pattern=pattern)
                if contains_pattern:
                    break
        
        # Else follow the pattern of the player before it and play a higher rank
        else:
            contains_pattern, pattern, choice, leading_rank = utils.smallest_valid_choice(hand=self.hand, pattern=pattern, leading_rank=leading_rank)
                
        # Return the card choice and subtract it from its hand
        if contains_pattern:
            choice = np.array(choice)
            self.hand -= choice
        return contains_pattern, pattern, choice, leading_rank, np.sum(self.hand)
    
class UserPlayer:
    def __init__(self, hand, moveset, free=False):
        self.hand = hand
        self.moveset = moveset
        self.free = free
        
    # The first card is the leading rank
    def move(self, pattern=None, prev_choice=None, leading_rank=-1):
        # Get the user input
        print(f"Hand: {utils.write_user_cards(self.hand)}")
        
        while True:
            valid_input = True
            if self.free:
                leading_rank = -1   # Reset the leading rank
                print("FREE TO MOVE")
                pattern = input("Enter the pattern: ")  # 1x5 format
                
                # Check if the pattern exists in the moveset
                if not pattern in self.moveset:
                    print("Invalid pattern. Please try again.")
                    print(self.hand, {utils.write_user_cards(self.hand)})
                    continue
                
            # Assumes the first card is the leading rank
            user_cards = input("Enter your move: ")    # 334455 format
            
            # Check if all cards are known in the card set
            for c in user_cards:
                if c not in CARDS.values():
                    valid_input = False
            
            if valid_input:
                contains_pattern, pattern, choice, user_rank, valid_input = utils.read_user_cards(user_cards, pattern, leading_rank, self.hand)   # Convert to numpy frequency array
                
            # Escape the while loop only if the input is valid
            if not valid_input:
                print("Invalid card selection. Please try again.")
                print(self.hand, {utils.write_user_cards(self.hand)})
            else:
                break
        
        # After a successful move, the player is no longer free to move
        self.free = False
            
        # Record the play
        if contains_pattern:
            choice = np.array(choice)
            self.hand -= choice
            leading_rank = user_rank
        return contains_pattern, pattern, choice, leading_rank, np.sum(self.hand)
        

env = GameEnv(num_decks=2, has_user=True, seed=0)
history = env.play_game()

# game_name = "user_game_0.pkl"
# pickle.dump(history, open(game_name, "wb"))
# history = pickle.load(open(game_name, "rb"))
# env.replay(history)
