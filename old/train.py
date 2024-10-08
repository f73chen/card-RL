import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import random
from collections import deque
from game_env import GameEnv

class ReplayBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self.buffer = []
        self.position = 0

    def push(self, state, action, reward, next_state, done):
        """Saves a transition."""
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        self.buffer[self.position] = (state, action, reward, next_state, done)
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size):
        """Samples a batch of transitions."""
        batch = random.sample(self.buffer, batch_size)
        state, action, reward, next_state, done = zip(*batch)
        return state, action, reward, next_state, done

    def __len__(self):
        return len(self.buffer)


def train(agent, target_agent, replay_buffer, optimizer, batch_size, gamma, device):
    """
    Trains the LSTM-DQN agent using a batch of transitions from the replay buffer.

    Params:
    - agent: The LSTM-DQN agent (current Q-network).
    - target_agent: The target Q-network (for stable updates).
    - replay_buffer: The replay buffer containing past transitions.
    - optimizer: Optimizer for updating the Q-network.
    - batch_size: The number of transitions to sample for each training step.
    - gamma: Discount factor for future rewards.
    - device: Device to perform computations on (e.g., 'cpu' or 'cuda').

    Returns:
    - loss: The computed loss for the batch.
    """
    
    # Ensure there's enough data in the buffer to sample a full batch
    if len(replay_buffer) < batch_size:
        return None

    # Sample a batch from the replay buffer
    state, action, reward, next_state, done = replay_buffer.sample(batch_size)

    # Convert to tensors and move to the appropriate device (e.g., GPU)
    state = torch.tensor(np.array(state), dtype=torch.float32).to(device)
    action = torch.tensor(action, dtype=torch.long).to(device)
    reward = torch.tensor(reward, dtype=torch.float32).to(device)
    next_state = torch.tensor(np.array(next_state), dtype=torch.float32).to(device)
    done = torch.tensor(done, dtype=torch.float32).to(device)

    # Forward pass: get current Q-values for the batch of states
    q_values = agent(state)  # (batch_size, num_actions)
    
    # Gather the Q-values for the actions that were actually taken
    q_value = q_values.gather(1, action.unsqueeze(1)).squeeze(1)  # (batch_size,)
    
    # Get the next state Q-values from the target network
    with torch.no_grad():
        next_q_values = target_agent(next_state)
        next_q_value = next_q_values.max(1)[0]  # Max Q-value for the next state

    # Compute the target Q-value
    target_q_value = reward + (1 - done) * gamma * next_q_value

    # Compute the loss
    loss = F.mse_loss(q_value, target_q_value)

    # Backpropagation
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    return loss.item()


# Hyperparameters
BATCH_SIZE = 32
GAMMA = 0.99
LR = 1e-4
EPSILON_START = 1.0
EPSILON_END = 0.1
EPSILON_DECAY = 5000  # Steps over which epsilon decays
TARGET_UPDATE_FREQUENCY = 1000  # How often to update the target network
REPLAY_BUFFER_CAPACITY = 10000
MAX_EPISODES = 10000
MAX_STEPS_PER_EPISODE = 500

# Initialize Game Environment, Agent, Target Agent, Replay Buffer, Optimizer
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Assuming `GameEnv` is the environment class you've created
env = GameEnv()

# Initialize the DQN and the target DQN agents
agent = LSTMDQNAgent(num_players=3, num_patterns=20, num_ranks=15, num_actions=100).to(device)
target_agent = LSTMDQNAgent(num_players=3, num_patterns=20, num_ranks=15, num_actions=100).to(device)

# Copy the weights of the main agent to the target agent
target_agent.load_state_dict(agent.state_dict())

# Optimizer
optimizer = optim.Adam(agent.parameters(), lr=LR)

# Replay buffer
replay_buffer = ReplayBuffer(REPLAY_BUFFER_CAPACITY)

# Exploration scheduling (epsilon-greedy)
epsilon = EPSILON_START
epsilon_decay = (EPSILON_START - EPSILON_END) / EPSILON_DECAY





def generate_new_samples():
    """Generate new samples by interacting with the environment."""
    for episode in range(MAX_EPISODES):
        state = env.reset()  # Reset the environment to get the initial state
        episode_reward = 0

        for step in range(MAX_STEPS_PER_EPISODE):
            # Select action based on epsilon-greedy policy
            valid_move, pattern, prev_choice, leading_rank, remainder = player.select_action(state, epsilon)
            action = (valid_move, pattern, prev_choice, leading_rank)   # Repackage it for step and recording

            # Take action in the environment and observe the result
            next_state, reward, done, _ = env.step(action)

            # Store the transition in the replay buffer
            replay_buffer.push(state, action, reward, next_state, done)

            # Update the current state
            state = next_state
            episode_reward += reward

            # If the episode is done, break the loop
            if done:
                break

        # After each episode, decay epsilon
        global epsilon
        epsilon = max(EPSILON_END, epsilon - epsilon_decay)

        # Train the agent after every episode
        if len(replay_buffer) >= BATCH_SIZE:
            train(agent, target_agent, replay_buffer, optimizer, BATCH_SIZE, GAMMA, device)

        # Update the target network every TARGET_UPDATE_FREQUENCY steps
        if episode % TARGET_UPDATE_FREQUENCY == 0:
            target_agent.load_state_dict(agent.state_dict())

        print(f"Episode {episode}, Total Reward: {episode_reward}, Epsilon: {epsilon:.4f}")


# Main training loop
generate_new_samples()




for episode in range(num_episodes):
    state = env.reset()
    
    # Buffer for storing transitions during the episode
    episode_transitions = []
    done = False
    while not done:
        # Agent 1's turn
        action_1 = agent.select_action(state['agent_1'])
        next_state, reward_1, done, _ = env.step(action_1)

        # Store transition (without immediately applying win/loss reward)
        episode_transitions.append((state['agent_1'], action_1, reward_1, next_state['agent_1'], done))

        # Move to the next player
        state = next_state

    # Once the game ends, finalize rewards based on final game result
    utils.finalize_rewards(mode=env.mode, num_players=env.num_players, episode_transitions=episode_transitions, winner=env.curr_player, landlord=env.landlord_idx)

    # Now update the agent for each transition in the episode
    for transition in episode_transitions:
        state, action, reward, next_state, done = transition
        agent.update(state, action, reward, next_state, done)


