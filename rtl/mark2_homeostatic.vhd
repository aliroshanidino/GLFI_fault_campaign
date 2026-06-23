-- ==============================================================================
-- Project: Scalable Neuromorphic Processor
-- Module: The Adaptive Homeostatic Izhikevich Neuron (Model 2 - No TMR)
-- Features: 4-Segment PWL, Beta Brake, Fast-Bleed, Safe Theta Clamping
-- Precision: Fixed-Point Q7.19 (26-bit: 1 Sign, 6 Integer, 19 Fractional)
-- ==============================================================================
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity homeostatic_neuron2 is
    Generic (
        WIDTH      : integer := 26  -- Q7.19 Format
    );
    Port (
        Clk        : in  STD_LOGIC;
        Reset      : in  STD_LOGIC;
        Enable     : in  STD_LOGIC;  
        I_syn      : in  signed(WIDTH-1 downto 0); 
        V_out      : out signed(WIDTH-1 downto 0);
        u_out      : out signed(WIDTH-1 downto 0);
        Theta_out  : out signed(WIDTH-1 downto 0); 
        Spike      : out STD_LOGIC
    );
end homeostatic_neuron2;

architecture Behavioral of homeostatic_neuron2 is
    
    -- State Registers
    signal v_reg     : signed(WIDTH-1 downto 0) := (others => '0');
    signal u_reg     : signed(WIDTH-1 downto 0) := to_signed(-106496, WIDTH); 
    signal theta_reg : signed(WIDTH-1 downto 0) := to_signed(576717, WIDTH); 
    
    -- PWL & V Datapath
    signal pwl_out      : signed(WIDTH-1 downto 0);
    signal v_shr_6      : signed(WIDTH-1 downto 0);
    signal term_1375    : signed(WIDTH-1 downto 0);
    signal sum_v1       : signed(WIDTH-1 downto 0);
    signal sum_v2       : signed(WIDTH-1 downto 0);
    signal dv           : signed(WIDTH-1 downto 0);
    signal v_next_raw   : signed(WIDTH-1 downto 0);
    signal v_clamped    : signed(WIDTH-1 downto 0);
    
    -- U Datapath
    signal b_v          : signed(WIDTH-1 downto 0);
    signal diff_u       : signed(WIDTH-1 downto 0);
    signal du           : signed(WIDTH-1 downto 0);
    signal u_next_raw   : signed(WIDTH-1 downto 0);
    
    -- Fast-Bleed & U Clamping
    signal bleed_target : signed(WIDTH-1 downto 0);
    signal u_fast_bleed : signed(WIDTH-1 downto 0);
    signal fast_bleed_en: STD_LOGIC;
    signal u_pre_clamp  : signed(WIDTH-1 downto 0);
    signal u_clamped    : signed(WIDTH-1 downto 0);
    
    -- Homeostasis Logic
    signal theta_err    : signed(WIDTH-1 downto 0);
    signal theta_decay  : signed(WIDTH-1 downto 0);
    signal theta_raw    : signed(WIDTH-1 downto 0);
    signal theta_jump_raw: signed(WIDTH-1 downto 0); -- [NEW] Added for safe calculation
    
    signal beta_brake   : signed(WIDTH-1 downto 0);
    signal u_jump_raw   : signed(WIDTH-1 downto 0);
    signal u_jump_clamped: signed(WIDTH-1 downto 0);

    -- Q7.19 Constants
    constant C_PARAM         : signed(WIDTH-1 downto 0) := to_signed(0, WIDTH);       
    constant D_PARAM         : signed(WIDTH-1 downto 0) := to_signed(49152, WIDTH);   
    constant U_REST          : signed(WIDTH-1 downto 0) := to_signed(-106496, WIDTH); 
    constant THETA_REST      : signed(WIDTH-1 downto 0) := to_signed(576717, WIDTH);  
    constant FAST_BLEED_TH   : signed(WIDTH-1 downto 0) := to_signed(-52429, WIDTH); 
    
    constant GAMMA_HW        : signed(WIDTH-1 downto 0) := to_signed(65536, WIDTH);  
    constant ALPHA_SHIFT     : integer := 6;                                         

    -- Hardware Clamps 
    constant V_MAX_HW        : signed(WIDTH-1 downto 0) := to_signed(2097152, WIDTH); -- 4.0 
    constant V_MIN_HW        : signed(WIDTH-1 downto 0) := to_signed(-262144, WIDTH); -- -0.5
    constant U_MAX_HW        : signed(WIDTH-1 downto 0) := to_signed(2097152, WIDTH); -- 4.0
    constant U_MIN_HW        : signed(WIDTH-1 downto 0) := to_signed(-2097152,WIDTH); -- -4.0
    
    -- [NEW] Safety Ceiling for Theta (8.0 in Q7.19) to prevent wrap-around
    constant THETA_MAX_HW    : signed(WIDTH-1 downto 0) := to_signed(4194304, WIDTH); 
    
    constant C_0_25          : signed(WIDTH-1 downto 0) := to_signed(131072, WIDTH);

begin

    -- 1. 4-Region PWL
    pwl_out <= (others => '0')                                           when v_reg(WIDTH-1) = '1' else
               shift_right(v_reg, 1)                                     when v_reg < to_signed(131072, WIDTH) else
               shift_left(v_reg, 1) - to_signed(196608, WIDTH)           when v_reg < to_signed(327680, WIDTH) else
               shift_left(v_reg, 2) - to_signed(851968, WIDTH)           when v_reg < to_signed(589824, WIDTH) else
               shift_left(v_reg, 3) - to_signed(3211264, WIDTH);

    v_shr_6    <= shift_right(v_reg, 6);
    term_1375  <= shift_right(v_reg, 3) + v_shr_6;
    sum_v1     <= pwl_out + I_syn;
    sum_v2     <= term_1375 + u_reg + C_0_25;
    dv         <= sum_v1 - sum_v2;
    v_next_raw <= v_reg + shift_right(dv, 6);

    v_clamped  <= V_MAX_HW when v_next_raw > V_MAX_HW else
                  V_MIN_HW when v_next_raw < V_MIN_HW else
                  v_next_raw;

    b_v        <= shift_right(v_reg, 2) - shift_right(v_reg, 4) + v_shr_6;
    diff_u     <= b_v - U_REST - u_reg;
    du         <= shift_right(diff_u, 6) + shift_right(diff_u, 8);
    u_next_raw <= u_reg + shift_right(du, 6);

    -- 2. Homeostasis Decay & Beta Brake
    theta_err   <= theta_reg - THETA_REST;
    theta_decay <= shift_right(theta_err, ALPHA_SHIFT);
    theta_raw   <= theta_reg - theta_decay;
    
    beta_brake  <= shift_left(theta_err, 3) when theta_err > to_signed(0, WIDTH) else (others => '0');
    
    u_jump_raw  <= u_clamped + D_PARAM + beta_brake;
    u_jump_clamped <= U_MAX_HW when u_jump_raw > U_MAX_HW else u_jump_raw;

    -- 3. Fast-Bleed Logic
    bleed_target <= u_next_raw + U_REST;
    u_fast_bleed <= shift_right(bleed_target, 1);
    
    fast_bleed_en <= '1' when (v_next_raw < FAST_BLEED_TH) and (theta_reg > THETA_REST) and (u_reg > U_REST) else '0';
    
    u_pre_clamp  <= u_fast_bleed when fast_bleed_en = '1' else u_next_raw;

    u_clamped    <= U_MAX_HW when u_pre_clamp > U_MAX_HW else
                    U_MIN_HW when u_pre_clamp < U_MIN_HW else
                    u_pre_clamp;

    -- [NEW] Calculate potential theta jump to check for overflow
    theta_jump_raw <= theta_raw + GAMMA_HW;

    -- 4. 1-Cycle State Update
    process(Clk, Reset)
    begin
        if Reset = '1' then
            v_reg     <= (others => '0');
            u_reg     <= U_REST; 
            theta_reg <= THETA_REST;
            Spike     <= '0';
        elsif rising_edge(Clk) then
            if Enable = '1' then
                if v_clamped >= theta_raw then
                    -- SPIKE EVENT
                    v_reg     <= C_PARAM; 
                    u_reg     <= u_jump_clamped;
                    
                    -- [NEW] Safe Theta Update (Prevents wrap-around on hard faults)
                    if theta_jump_raw > THETA_MAX_HW then
                        theta_reg <= THETA_MAX_HW;
                    else
                        theta_reg <= theta_jump_raw;
                    end if;
                    
                    Spike     <= '1';
                else
                    -- NORMAL DYNAMICS
                    v_reg     <= v_clamped;
                    u_reg     <= u_clamped;
                    theta_reg <= theta_raw; 
                    Spike     <= '0';
                end if;
            else
                Spike <= '0';
            end if;
        end if;
    end process;

    V_out     <= v_reg;
    u_out     <= u_reg;
    Theta_out <= theta_reg;

end Behavioral;