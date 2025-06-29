# Mantra Refactor Code Examples

## Example 1: State Machine Implementation

### Before: Implicit State Management
```python
# In mantras.py - state scattered everywhere
class MantraSystem:
    def __init__(self):
        self.active_challenges = {}  # user_id -> challenge dict
        self.user_streaks = {}  # user_id -> streak data
        
    async def send_mantra(self, user):
        if user.id in self.active_challenges:
            return  # Already has one
            
        self.active_challenges[user.id] = {
            "mantra": mantra,
            "sent_at": datetime.now(),
            "theme": theme,
            "timeout_count": 0
        }
```

### After: Explicit State Machine
```python
# models/user_state.py
@dataclass
class MantraContext:
    mantra: str
    theme: str
    sent_at: datetime
    attempts: int = 0
    delay_until: Optional[datetime] = None

# core/state_machine.py
class MantraStateMachine:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.state = "idle"
        self.context = MantraContext()
        
    async def can_send_mantra(self) -> bool:
        return self.state == "idle"
        
    async def start_encounter(self, mantra: str, theme: str):
        if self.state != "idle":
            raise InvalidStateError(f"Cannot start from {self.state}")
            
        self.state = "pending"
        self.context = MantraContext(
            mantra=mantra, 
            theme=theme,
            sent_at=datetime.now()
        )
        await self.save_state()
```

## Example 2: Feature Plugin System

### Before: Hardcoded Features
```python
# Everything mixed in mantras.py
async def handle_mantra_response(self, user, response):
    # Calculate points
    base_points = 10
    speed_bonus = 5 if response_time < 30 else 0
    
    # Check for forced delay (hardcoded)
    if streak > 10 and response_time < 20:
        await user.send("Processing delay required...")
        await asyncio.sleep(120)
```

### After: Pluggable Features
```python
# features/base.py
class Feature(ABC):
    @abstractmethod
    async def on_response_received(self, context: ResponseContext) -> FeatureResult:
        pass

# features/forced_delay.py
class ForcedDelayFeature(Feature):
    async def on_response_received(self, context: ResponseContext) -> FeatureResult:
        if self.should_delay(context):
            delay = self.calculate_delay(context)
            return FeatureResult(
                action="delay",
                duration=delay,
                message="Neural pathways require additional processing time..."
            )
        return FeatureResult(action="continue")
    
    def should_delay(self, context):
        return (context.streak >= 10 and 
                context.response_time < 20 and
                random.random() < 0.25)

# core/feature_manager.py
class FeatureManager:
    def __init__(self):
        self.features = []
        
    def register(self, feature: Feature):
        self.features.append(feature)
        
    async def process_response(self, context: ResponseContext):
        for feature in self.features:
            result = await feature.on_response_received(context)
            if result.action != "continue":
                return result
        return FeatureResult(action="continue")
```

## Example 3: Game Mode Abstraction

### Before: Monolithic Delivery
```python
# All in one giant method
async def deliver_mantras(self):
    for config in configs:
        if should_send_mantra(config):
            mantra = select_mantra(config)
            embed = create_embed(mantra)
            view = MantraRequestView(timeout=1800)
            await user.send(embed=embed, view=view)
```

### After: Game Mode Pattern
```python
# game_modes/base.py
class GameMode(ABC):
    @abstractmethod
    async def create_encounter(self, user_state) -> Encounter:
        pass
        
    @abstractmethod
    async def present_encounter(self, encounter: Encounter) -> Message:
        pass
        
    @abstractmethod
    async def handle_response(self, encounter: Encounter, response: str) -> Result:
        pass

# game_modes/classic.py
class ClassicMode(GameMode):
    async def create_encounter(self, user_state) -> Encounter:
        mantra = self.content_manager.select_mantra(user_state.themes)
        return Encounter(
            type="classic",
            content=mantra,
            timeout=1800,
            points=self.calculate_points(user_state)
        )
    
    async def present_encounter(self, encounter: Encounter) -> Message:
        embed = self.create_classic_embed(encounter)
        view = ClassicMantraView(encounter)
        return await encounter.user.send(embed=embed, view=view)

# game_modes/session.py
class SessionMode(GameMode):
    async def create_encounter(self, user_state) -> Encounter:
        session = self.create_session(user_state)
        return Encounter(
            type="session",
            content=session.first_prompt,
            timeout=300,
            session_id=session.id
        )
```

## Example 4: Progression System Integration

### Before: Simple Points
```python
# Just track total points
config["total_points_earned"] += points
```

### After: Full Progression
```python
# models/progression.py
@dataclass
class UserProgression:
    xp: int = 0
    level: int = 1
    ct_balance: int = 0
    unlocked_themes: Set[str] = field(default_factory=set)
    unlocked_pets: Set[str] = field(default_factory=set)
    achievements: List[str] = field(default_factory=list)

# core/progression.py
class ProgressionEngine:
    def process_encounter_completion(self, encounter: CompletedEncounter):
        # Award XP
        xp_gained = self.calculate_xp(encounter)
        user_prog = self.get_user_progression(encounter.user_id)
        user_prog.xp += xp_gained
        
        # Check level up
        new_level = self.calculate_level(user_prog.xp)
        if new_level > user_prog.level:
            await self.handle_level_up(user_prog, new_level)
            
        # Award currency
        ct_gained = self.calculate_ct(encounter)
        user_prog.ct_balance += ct_gained
        
        # Check achievements
        new_achievements = self.check_achievements(encounter, user_prog)
        user_prog.achievements.extend(new_achievements)
        
        return ProgressionResult(
            xp_gained=xp_gained,
            ct_gained=ct_gained,
            level_up=new_level > user_prog.level,
            new_unlocks=self.check_unlocks(user_prog),
            achievements=new_achievements
        )
```

## Example 5: View Separation

### Before: Business Logic in Views
```python
# utils/ui.py - View doing too much
class MantraRequestView(discord.ui.View):
    async def on_timeout(self):
        config = get_user_mantra_config(self.bot.config, self.user)
        config["timeout_count"] = config.get("timeout_count", 0) + 1
        
        if config["timeout_count"] >= 3:
            config["frequency"] = max(1.0, config["frequency"] - 0.5)
            
        log_encounter(self.user.id, {
            "completed": False,
            "theme": self.theme
        })
        
        save_user_mantra_config(self.bot.config, self.user, config)
```

### After: View Just Handles UI
```python
# views/mantra_views.py
class MantraRequestView(discord.ui.View):
    def __init__(self, encounter_id: str, callbacks: ViewCallbacks):
        super().__init__(timeout=1800)
        self.encounter_id = encounter_id
        self.callbacks = callbacks
        
    async def on_timeout(self):
        # Just notify the callback
        await self.callbacks.on_timeout(self.encounter_id)
        
    @discord.ui.button(label="Request Extension")
    async def request_extension(self, interaction, button):
        result = await self.callbacks.on_extension_request(
            self.encounter_id, 
            interaction.user.id
        )
        await interaction.response.send_message(
            result.message, 
            ephemeral=True
        )

# core/delivery.py
class MantraDelivery:
    async def handle_timeout(self, encounter_id: str):
        # All business logic here
        encounter = self.get_encounter(encounter_id)
        state = await self.state_manager.get_state(encounter.user_id)
        
        # Update state
        await state.transition("timeout")
        
        # Apply timeout effects
        progression = await self.progression.handle_timeout(encounter)
        
        # Log the event
        await self.logger.log_encounter(encounter, completed=False)
        
        # Schedule next
        await self.scheduler.schedule_next(encounter.user_id)
```

## Migration Pattern

For each refactor:
1. **Create new structure** without breaking old code
2. **Implement new pattern** alongside existing
3. **Gradually move logic** from old to new
4. **Update references** one at a time
5. **Remove old code** once fully migrated

This allows incremental changes without breaking the bot!