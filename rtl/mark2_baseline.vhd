-- ==============================================================================
-- Project: Scalable Neuromorphic Processor
-- Module: Application-Specific Izhikevich Neuron (Model 1 - Baseline)
-- Features: 1-Cycle Unrolled Datapath, Zero-Multiplier, 4-Segment PWL
-- Precision: Fixed-Point Q7.19 (26-bit: 1 Sign, 6 Integer, 19 Fractional)
-- ==============================================================================
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity baseline_neuron2 is
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
        Spike      : out STD_LOGIC
    );
end baseline_neuron2;

architecture Behavioral of baseline_neuron2 is
    
    -- State Registers
    signal v_reg : signed(WIDTH-1 downto 0) := (others => '0');
    signal u_reg : signed(WIDTH-1 downto 0) := (others => '0'); 
    
    -- Combinational Signals
    signal pwl_out      : signed(WIDTH-1 downto 0);
    signal v_shr_6      : signed(WIDTH-1 downto 0);
    signal term_1375    : signed(WIDTH-1 downto 0);
    signal sum_v1       : signed(WIDTH-1 downto 0);
    signal sum_v2       : signed(WIDTH-1 downto 0);
    signal dv           : signed(WIDTH-1 downto 0);
    signal v_next_raw   : signed(WIDTH-1 downto 0);
    signal v_clamped    : signed(WIDTH-1 downto 0);
    
    signal b_v          : signed(WIDTH-1 downto 0);
    signal diff_u       : signed(WIDTH-1 downto 0);
    signal du           : signed(WIDTH-1 downto 0);
    signal u_next_raw   : signed(WIDTH-1 downto 0);
    signal u_clamped    : signed(WIDTH-1 downto 0);
    
    signal u_jump_raw   : signed(WIDTH-1 downto 0);
    signal u_jump_clamped: signed(WIDTH-1 downto 0);

    -- Q7.19 Constants
    constant C_PARAM    : signed(WIDTH-1 downto 0) := to_signed(0, WIDTH);          -- Reset V = 0.0
    constant D_PARAM    : signed(WIDTH-1 downto 0) := to_signed(49152, WIDTH);      -- Jump d = 0.09375
    constant U_OFFSET   : signed(WIDTH-1 downto 0) := to_signed(106496, WIDTH);     -- Offset = 0.203125
    
    constant THETA_BASE : signed(WIDTH-1 downto 0) := to_signed(576717, WIDTH);     -- Spike Threshold (1.1)
    constant V_MAX_HW   : signed(WIDTH-1 downto 0) := to_signed(778240, WIDTH);     -- V Clamp High (1.484)
    constant V_MIN_HW   : signed(WIDTH-1 downto 0) := to_signed(-262144,WIDTH);     -- V Clamp Low (-0.5)
    constant U_MAX_HW   : signed(WIDTH-1 downto 0) := to_signed(2097152,WIDTH);     -- U Clamp High (4.0)
    constant U_MIN_HW   : signed(WIDTH-1 downto 0) := to_signed(-2097152,WIDTH);    -- U Clamp Low (-4.0)
    
    constant C_0_25     : signed(WIDTH-1 downto 0) := to_signed(131072, WIDTH);     -- 0.25 constant

begin

    -- 1. Optimized 4-Region PWL
    pwl_out <= (others => '0')                                           when v_reg(WIDTH-1) = '1' else
               shift_right(v_reg, 1)                                     when v_reg < to_signed(131072, WIDTH) else
               shift_left(v_reg, 1) - to_signed(196608, WIDTH)           when v_reg < to_signed(327680, WIDTH) else
               shift_left(v_reg, 2) - to_signed(851968, WIDTH)           when v_reg < to_signed(589824, WIDTH) else
               shift_left(v_reg, 3) - to_signed(3211264, WIDTH);

    -- 2. Voltage Datapath
    v_shr_6    <= shift_right(v_reg, 6);
    term_1375  <= shift_right(v_reg, 3) + v_shr_6;
    sum_v1     <= pwl_out + I_syn;
    sum_v2     <= term_1375 + u_reg + C_0_25;
    dv         <= sum_v1 - sum_v2;
    v_next_raw <= v_reg + shift_right(dv, 6);

    v_clamped  <= V_MAX_HW when v_next_raw > V_MAX_HW else
                  V_MIN_HW when v_next_raw < V_MIN_HW else
                  v_next_raw;

    -- 3. Recovery Datapath 
    b_v        <= shift_right(v_reg, 2) - shift_right(v_reg, 4) + v_shr_6;
    diff_u     <= b_v - U_OFFSET - u_reg;
    du         <= shift_right(diff_u, 6) + shift_right(diff_u, 8);
    u_next_raw <= u_reg + shift_right(du, 6);

    u_clamped  <= U_MAX_HW when u_next_raw > U_MAX_HW else
                  U_MIN_HW when u_next_raw < U_MIN_HW else
                  u_next_raw;
                  
    u_jump_raw <= u_clamped + D_PARAM;
    u_jump_clamped <= U_MAX_HW when u_jump_raw > U_MAX_HW else u_jump_raw;

    -- 4. 1-Cycle State Update
    process(Clk, Reset)
    begin
        if Reset = '1' then
            v_reg <= (others => '0');
            u_reg <= -U_OFFSET; 
            Spike <= '0';
        elsif rising_edge(Clk) then
            if Enable = '1' then
                if v_clamped >= THETA_BASE then
                    v_reg <= C_PARAM;         
                    u_reg <= u_jump_clamped;
                    Spike <= '1';
                else
                    v_reg <= v_clamped;
                    u_reg <= u_clamped;
                    Spike <= '0';
                end if;
            else
                Spike <= '0';
            end if;
        end if;
    end process;

    V_out <= v_reg;
    u_out <= u_reg;

end Behavioral;