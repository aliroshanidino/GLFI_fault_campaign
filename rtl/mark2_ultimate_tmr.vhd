-- ==============================================================================
-- Project: Scalable Neuromorphic Processor
-- Module: Heavyweight TMR Homeostatic Neuron (Model 4 - Ultimate Resilient)
-- Features: 4-Segment PWL, V_reg/U_reg/Theta_reg TMR, Control-Plane TMR
-- Precision: Fixed-Point Q7.19 (26-bit: 1 Sign, 6 Integer, 19 Fractional)
-- ==============================================================================
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity ultimate_tmr_neuron2 is
    Generic ( WIDTH : integer := 26 );
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
end ultimate_tmr_neuron2;

architecture Behavioral of ultimate_tmr_neuron2 is
    
    -- 1. Triplicated State Registers (V, U, Theta)
    signal v_reg_A, v_reg_B, v_reg_C             : signed(WIDTH-1 downto 0) := (others => '0');
    signal u_reg_A, u_reg_B, u_reg_C             : signed(WIDTH-1 downto 0) := to_signed(-106496, WIDTH); 
    signal theta_reg_A, theta_reg_B, theta_reg_C : signed(WIDTH-1 downto 0) := to_signed(576717, WIDTH);
    
    -- Voted Registers (To feed the simplex datapath)
    signal v_voted, u_voted, voted_theta : signed(WIDTH-1 downto 0);

    -- 2. Unprotected Combinational Datapath (Simplex Cloud)
    signal pwl_out, v_shr_6, term_1375       : signed(WIDTH-1 downto 0);
    signal sum_v1, sum_v2, dv, v_next_raw    : signed(WIDTH-1 downto 0);
    signal v_clamped                         : signed(WIDTH-1 downto 0);
    signal b_v, diff_u, du, u_next_raw       : signed(WIDTH-1 downto 0);
    signal bleed_target, u_fast_bleed        : signed(WIDTH-1 downto 0);
    signal u_pre_clamp, u_clamped            : signed(WIDTH-1 downto 0);
    
    signal simplex_theta_err : signed(WIDTH-1 downto 0);
    signal beta_brake_val    : signed(WIDTH-1 downto 0);
    signal beta_brake        : signed(WIDTH-1 downto 0);
    signal u_jump_raw, u_jump_clamped : signed(WIDTH-1 downto 0);

    -- 3. Triplicated Control Logic
    signal theta_err_A, theta_err_B, theta_err_C       : signed(WIDTH-1 downto 0);
    signal theta_decay_A, theta_decay_B, theta_decay_C : signed(WIDTH-1 downto 0);
    signal theta_raw_A, theta_raw_B, theta_raw_C       : signed(WIDTH-1 downto 0);
    signal theta_jmp_A, theta_jmp_B, theta_jmp_C       : signed(WIDTH-1 downto 0);

    signal f_spk_A, f_spk_B, f_spk_C       : std_logic;
    signal f_beta_A, f_beta_B, f_beta_C    : std_logic;
    signal f_fb_A, f_fb_B, f_fb_C          : std_logic;
    signal f_vmax_A, f_vmax_B, f_vmax_C    : std_logic;
    signal f_vmin_A, f_vmin_B, f_vmin_C    : std_logic;
    signal f_umax_A, f_umax_B, f_umax_C    : std_logic;
    signal f_umin_A, f_umin_B, f_umin_C    : std_logic;

    signal voted_spk, voted_beta, voted_fb : std_logic;
    signal voted_vmax, voted_vmin          : std_logic;
    signal voted_umax, voted_umin          : std_logic;

    -- Constants (Q7.19)
    constant C_PARAM       : signed(WIDTH-1 downto 0) := to_signed(0, WIDTH);       
    constant D_PARAM       : signed(WIDTH-1 downto 0) := to_signed(49152, WIDTH);   
    constant U_REST        : signed(WIDTH-1 downto 0) := to_signed(-106496, WIDTH); 
    constant THETA_REST    : signed(WIDTH-1 downto 0) := to_signed(576717, WIDTH);  
    constant FAST_BLEED_TH : signed(WIDTH-1 downto 0) := to_signed(-52429, WIDTH); 
    constant GAMMA_HW      : signed(WIDTH-1 downto 0) := to_signed(65536, WIDTH);  
    constant ALPHA_SHIFT   : integer := 6;                                         
    constant V_MAX_HW      : signed(WIDTH-1 downto 0) := to_signed(2097152, WIDTH); 
    constant V_MIN_HW      : signed(WIDTH-1 downto 0) := to_signed(-262144, WIDTH); 
    constant U_MAX_HW      : signed(WIDTH-1 downto 0) := to_signed(2097152, WIDTH); 
    constant U_MIN_HW      : signed(WIDTH-1 downto 0) := to_signed(-2097152,WIDTH); 
    constant THETA_MAX_HW  : signed(WIDTH-1 downto 0) := to_signed(4194304, WIDTH); 
    constant C_0_25        : signed(WIDTH-1 downto 0) := to_signed(131072, WIDTH);

    -- Synthesis Attributes
    attribute keep : string;
    attribute keep of f_spk_A, f_spk_B, f_spk_C       : signal is "true";
    attribute keep of f_beta_A, f_beta_B, f_beta_C    : signal is "true";
    attribute keep of f_fb_A, f_fb_B, f_fb_C          : signal is "true";
    attribute keep of f_vmax_A, f_vmax_B, f_vmax_C    : signal is "true";
    attribute keep of f_vmin_A, f_vmin_B, f_vmin_C    : signal is "true";
    attribute keep of f_umax_A, f_umax_B, f_umax_C    : signal is "true";
    attribute keep of f_umin_A, f_umin_B, f_umin_C    : signal is "true";
    attribute keep of v_reg_A, v_reg_B, v_reg_C       : signal is "true";
    attribute keep of u_reg_A, u_reg_B, u_reg_C       : signal is "true";
    attribute keep of theta_reg_A, theta_reg_B, theta_reg_C : signal is "true";

begin

    -- ------------------------------------------------------------------------
    -- MAJORITY VOTERS (Bitwise 26-bit and 1-bit)
    -- ------------------------------------------------------------------------
    v_voted     <= (v_reg_A and v_reg_B) or (v_reg_B and v_reg_C) or (v_reg_A and v_reg_C);
    u_voted     <= (u_reg_A and u_reg_B) or (u_reg_B and u_reg_C) or (u_reg_A and u_reg_C);
    voted_theta <= (theta_reg_A and theta_reg_B) or (theta_reg_B and theta_reg_C) or (theta_reg_A and theta_reg_C);

    -- ------------------------------------------------------------------------
    -- DATAPATH (Simplex Cloud fed by Voted Registers)
    -- ------------------------------------------------------------------------
    pwl_out <= (others => '0')                                           when v_voted(WIDTH-1) = '1' else
               shift_right(v_voted, 1)                                   when v_voted < to_signed(131072, WIDTH) else
               shift_left(v_voted, 1) - to_signed(196608, WIDTH)         when v_voted < to_signed(327680, WIDTH) else
               shift_left(v_voted, 2) - to_signed(851968, WIDTH)         when v_voted < to_signed(589824, WIDTH) else
               shift_left(v_voted, 3) - to_signed(3211264, WIDTH);

    v_shr_6    <= shift_right(v_voted, 6);
    term_1375  <= shift_right(v_voted, 3) + v_shr_6;
    sum_v1     <= pwl_out + I_syn;
    sum_v2     <= term_1375 + u_voted + C_0_25;
    dv         <= sum_v1 - sum_v2;
    v_next_raw <= v_voted + shift_right(dv, 6);

    b_v        <= shift_right(v_voted, 2) - shift_right(v_voted, 4) + v_shr_6;
    diff_u     <= b_v - U_REST - u_voted;
    du         <= shift_right(diff_u, 6) + shift_right(diff_u, 8);
    u_next_raw <= u_voted + shift_right(du, 6);

    bleed_target <= u_next_raw + U_REST;
    u_fast_bleed <= shift_right(bleed_target, 1);

    -- ------------------------------------------------------------------------
    -- TRIPLICATED CONTROL-PLANE
    -- ------------------------------------------------------------------------
    f_vmax_A <= '1' when v_next_raw > V_MAX_HW else '0';
    f_vmax_B <= '1' when v_next_raw > V_MAX_HW else '0';
    f_vmax_C <= '1' when v_next_raw > V_MAX_HW else '0';
    voted_vmax <= (f_vmax_A and f_vmax_B) or (f_vmax_B and f_vmax_C) or (f_vmax_A and f_vmax_C);

    f_vmin_A <= '1' when v_next_raw < V_MIN_HW else '0';
    f_vmin_B <= '1' when v_next_raw < V_MIN_HW else '0';
    f_vmin_C <= '1' when v_next_raw < V_MIN_HW else '0';
    voted_vmin <= (f_vmin_A and f_vmin_B) or (f_vmin_B and f_vmin_C) or (f_vmin_A and f_vmin_C);

    v_clamped <= V_MAX_HW when voted_vmax = '1' else
                 V_MIN_HW when voted_vmin = '1' else
                 v_next_raw;

    f_fb_A <= '1' when (v_next_raw < FAST_BLEED_TH) and (theta_reg_A > THETA_REST) and (u_voted > U_REST) else '0';
    f_fb_B <= '1' when (v_next_raw < FAST_BLEED_TH) and (theta_reg_B > THETA_REST) and (u_voted > U_REST) else '0';
    f_fb_C <= '1' when (v_next_raw < FAST_BLEED_TH) and (theta_reg_C > THETA_REST) and (u_voted > U_REST) else '0';
    voted_fb <= (f_fb_A and f_fb_B) or (f_fb_B and f_fb_C) or (f_fb_A and f_fb_C);

    u_pre_clamp <= u_fast_bleed when voted_fb = '1' else u_next_raw;

    f_umax_A <= '1' when u_pre_clamp > U_MAX_HW else '0';
    f_umax_B <= '1' when u_pre_clamp > U_MAX_HW else '0';
    f_umax_C <= '1' when u_pre_clamp > U_MAX_HW else '0';
    voted_umax <= (f_umax_A and f_umax_B) or (f_umax_B and f_umax_C) or (f_umax_A and f_umax_C);

    f_umin_A <= '1' when u_pre_clamp < U_MIN_HW else '0';
    f_umin_B <= '1' when u_pre_clamp < U_MIN_HW else '0';
    f_umin_C <= '1' when u_pre_clamp < U_MIN_HW else '0';
    voted_umin <= (f_umin_A and f_umin_B) or (f_umin_B and f_umin_C) or (f_umin_A and f_umin_C);

    u_clamped <= U_MAX_HW when voted_umax = '1' else
                 U_MIN_HW when voted_umin = '1' else
                 u_pre_clamp;

    theta_err_A <= theta_reg_A - THETA_REST;
    theta_err_B <= theta_reg_B - THETA_REST;
    theta_err_C <= theta_reg_C - THETA_REST;

    theta_decay_A <= shift_right(theta_err_A, ALPHA_SHIFT);
    theta_decay_B <= shift_right(theta_err_B, ALPHA_SHIFT);
    theta_decay_C <= shift_right(theta_err_C, ALPHA_SHIFT);

    theta_raw_A <= theta_reg_A - theta_decay_A;
    theta_raw_B <= theta_reg_B - theta_decay_B;
    theta_raw_C <= theta_reg_C - theta_decay_C;

    theta_jmp_A <= theta_raw_A + GAMMA_HW;
    theta_jmp_B <= theta_raw_B + GAMMA_HW;
    theta_jmp_C <= theta_raw_C + GAMMA_HW;

    f_beta_A <= '1' when theta_err_A > to_signed(0, WIDTH) else '0';
    f_beta_B <= '1' when theta_err_B > to_signed(0, WIDTH) else '0';
    f_beta_C <= '1' when theta_err_C > to_signed(0, WIDTH) else '0';
    voted_beta <= (f_beta_A and f_beta_B) or (f_beta_B and f_beta_C) or (f_beta_A and f_beta_C);

    simplex_theta_err <= voted_theta - THETA_REST;
    beta_brake_val <= shift_left(simplex_theta_err, 3);
    beta_brake <= beta_brake_val when voted_beta = '1' else (others => '0');

    u_jump_raw <= u_clamped + D_PARAM + beta_brake;
    u_jump_clamped <= U_MAX_HW when u_jump_raw > U_MAX_HW else u_jump_raw;

    f_spk_A <= '1' when v_clamped >= theta_raw_A else '0';
    f_spk_B <= '1' when v_clamped >= theta_raw_B else '0';
    f_spk_C <= '1' when v_clamped >= theta_raw_C else '0';
    voted_spk <= (f_spk_A and f_spk_B) or (f_spk_B and f_spk_C) or (f_spk_A and f_spk_C);

    -- ------------------------------------------------------------------------
    -- 1-CYCLE TRIPLICATED STATE UPDATE
    -- ------------------------------------------------------------------------
    process(Clk, Reset)
    begin
        if Reset = '1' then
            v_reg_A <= (others => '0'); v_reg_B <= (others => '0'); v_reg_C <= (others => '0');
            u_reg_A <= U_REST;          u_reg_B <= U_REST;          u_reg_C <= U_REST; 
            theta_reg_A <= THETA_REST;  theta_reg_B <= THETA_REST;  theta_reg_C <= THETA_REST;
            Spike <= '0';
        elsif rising_edge(Clk) then
            if Enable = '1' then
                Spike <= voted_spk;
                
                if voted_spk = '1' then
                    v_reg_A <= C_PARAM; v_reg_B <= C_PARAM; v_reg_C <= C_PARAM; 
                    u_reg_A <= u_jump_clamped; u_reg_B <= u_jump_clamped; u_reg_C <= u_jump_clamped;
                    
                    if theta_jmp_A > THETA_MAX_HW then theta_reg_A <= THETA_MAX_HW; else theta_reg_A <= theta_jmp_A; end if;
                    if theta_jmp_B > THETA_MAX_HW then theta_reg_B <= THETA_MAX_HW; else theta_reg_B <= theta_jmp_B; end if;
                    if theta_jmp_C > THETA_MAX_HW then theta_reg_C <= THETA_MAX_HW; else theta_reg_C <= theta_jmp_C; end if;
                else
                    v_reg_A <= v_clamped; v_reg_B <= v_clamped; v_reg_C <= v_clamped;
                    u_reg_A <= u_clamped; u_reg_B <= u_clamped; u_reg_C <= u_clamped;
                    
                    theta_reg_A <= theta_raw_A;
                    theta_reg_B <= theta_raw_B;
                    theta_reg_C <= theta_raw_C;
                end if;
            else
                Spike <= '0';
            end if;
        end if;
    end process;

    V_out <= v_voted;
    u_out <= u_voted;
    Theta_out <= voted_theta;

end Behavioral;