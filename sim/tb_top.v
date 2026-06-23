// sim/tb_top.v
`timescale 1ns/1ps

// ============================================================================
// Yosys Generic Simulation Library
// ============================================================================

module \$_AND_ (input A, input B, output Y); assign Y = A & B; endmodule
module \$_OR_  (input A, input B, output Y); assign Y = A | B; endmodule
module \$_XOR_ (input A, input B, output Y); assign Y = A ^ B; endmodule
module \$_NAND_ (input A, input B, output Y); assign Y = ~(A & B); endmodule
module \$_NOR_  (input A, input B, output Y); assign Y = ~(A | B); endmodule
module \$_XNOR_ (input A, input B, output Y); assign Y = ~(A ^ B); endmodule
module \$_NOT_  (input A, output Y);          assign Y = ~A; endmodule
module \$_MUX_  (input A, input B, input S, output Y); assign Y = S ? B : A; endmodule

// Flip-Flops
// PP0: Posedge Clock, Posedge Reset, Reset Value = 0
module \$_DFF_PP0_ (input C, input R, input D, output reg Q);
    always @(posedge C or posedge R) begin
        if (R) Q <= 1'b0;
        else   Q <= D;
    end
endmodule

// PP1: Posedge Clock, Posedge Reset, Reset Value = 1
module \$_DFF_PP1_ (input C, input R, input D, output reg Q);
    always @(posedge C or posedge R) begin
        if (R) Q <= 1'b1;
        else   Q <= D;
    end
endmodule

// P_: Posedge Clock (No Reset)
module \$_DFF_P_ (input C, input D, output reg Q);
    always @(posedge C) begin
        Q <= D;
    end
endmodule
// ============================================================================

// ============================================================================
// Top Level Testbench Envelope
// ============================================================================
module tb_top;
    
    // System Signals
    reg Clk;
    reg Reset;
    reg Enable;
    reg [25:0] I_syn;
    
    // Outputs
    wire [25:0] V_out;
    wire [25:0] u_out;
    wire Spike;
    
    // Fault Bus Signals (Driven by Cocotb)
    reg fi_enable;
    reg [31:0] fi_target_id;
    reg fi_value;

    // VCD Dumping for Waveform Analysis
    // initial begin
    //     $dumpfile("waveform.vcd");
    //     $dumpvars(0, tb_top);
    // end

endmodule